from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class CsvImportError(ValueError):
    """Raised when a product CSV cannot be parsed or imported."""


_HANDLE_RE = re.compile(r"[^a-z0-9]+")


def slugify_handle(value: str) -> str:
    slug = _HANDLE_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "product"


def _cell(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row and row[name] is not None and str(row[name]).strip():
            return str(row[name]).strip()
        # Case-insensitive fallback
        lowered = {k.lower(): k for k in row}
        key = lowered.get(name.lower())
        if key is not None and row[key] is not None and str(row[key]).strip():
            return str(row[key]).strip()
    return ""


def _truthy(value: str) -> bool | None:
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized in {"true", "1", "yes", "y", "active", "published"}:
        return True
    if normalized in {"false", "0", "no", "n", "draft", "unpublished"}:
        return False
    return None


def _status_from_row(row: dict[str, str]) -> str:
    status = _cell(row, "Status").upper()
    if status in {"ACTIVE", "DRAFT", "ARCHIVED"}:
        return status
    published = _truthy(_cell(row, "Published"))
    if published is True:
        return "ACTIVE"
    if published is False:
        return "DRAFT"
    return "DRAFT"


def _split_tags(raw: str) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass
class ParsedVariant:
    option_values: list[dict[str, str]]
    price: str | None = None
    compare_at_price: str | None = None
    sku: str | None = None
    barcode: str | None = None
    weight: float | None = None
    weight_unit: str | None = None
    taxable: bool | None = None
    inventory_qty: int | None = None


@dataclass
class ParsedProduct:
    handle: str
    title: str
    description_html: str = ""
    vendor: str = ""
    product_type: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = "DRAFT"
    options: list[dict[str, Any]] = field(default_factory=list)
    variants: list[ParsedVariant] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    seo_title: str = ""
    seo_description: str = ""
    source_rows: int = 0


def load_csv_text(csv_text: str = "", csv_path: str = "") -> str:
    if csv_text.strip():
        return csv_text
    if csv_path.strip():
        path = Path(csv_path).expanduser()
        if not path.is_file():
            raise CsvImportError(f"CSV file not found: {path}")
        return path.read_text(encoding="utf-8-sig")
    raise CsvImportError("Provide csv_text or csv_path.")


def parse_products_csv(csv_text: str) -> list[ParsedProduct]:
    """Parse a Shopify-style product CSV into product groups keyed by Handle."""
    if not csv_text.strip():
        raise CsvImportError("CSV is empty.")

    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise CsvImportError("CSV has no header row.")

    products: dict[str, ParsedProduct] = {}
    order: list[str] = []

    for index, raw_row in enumerate(reader, start=2):
        row = {str(k): ("" if v is None else str(v)) for k, v in raw_row.items() if k}
        handle = _cell(row, "Handle")
        title = _cell(row, "Title")
        if not handle:
            if title:
                handle = slugify_handle(title)
            else:
                raise CsvImportError(f"Row {index}: missing Handle (and Title).")

        product = products.get(handle)
        if product is None:
            if not title:
                raise CsvImportError(
                    f"Row {index}: first row for handle '{handle}' needs a Title."
                )
            product = ParsedProduct(
                handle=handle,
                title=title,
                description_html=_cell(row, "Body (HTML)", "Body HTML", "Description"),
                vendor=_cell(row, "Vendor"),
                product_type=_cell(row, "Type", "Product Type"),
                tags=_split_tags(_cell(row, "Tags")),
                status=_status_from_row(row),
                seo_title=_cell(row, "SEO Title"),
                seo_description=_cell(row, "SEO Description"),
            )
            products[handle] = product
            order.append(handle)
        else:
            # Fill blanks from later rows (Shopify export often repeats only some fields)
            if not product.description_html:
                product.description_html = _cell(
                    row, "Body (HTML)", "Body HTML", "Description"
                )
            if not product.vendor:
                product.vendor = _cell(row, "Vendor")
            if not product.product_type:
                product.product_type = _cell(row, "Type", "Product Type")
            if not product.tags:
                product.tags = _split_tags(_cell(row, "Tags"))

        product.source_rows += 1

        option_defs: list[tuple[str, str]] = []
        for i in (1, 2, 3):
            name = _cell(row, f"Option{i} Name")
            value = _cell(row, f"Option{i} Value")
            if name and value:
                option_defs.append((name, value))

        if option_defs:
            existing = {opt["name"]: opt for opt in product.options}
            for name, value in option_defs:
                opt = existing.get(name)
                if opt is None:
                    opt = {"name": name, "values": []}
                    product.options.append(opt)
                    existing[name] = opt
                values = opt["values"]
                if value not in values:
                    values.append(value)

        price = _cell(row, "Variant Price", "Price")
        compare_at = _cell(row, "Variant Compare At Price", "Compare At Price")
        sku = _cell(row, "Variant SKU", "SKU")
        barcode = _cell(row, "Variant Barcode", "Barcode")
        grams = _cell(row, "Variant Grams")
        weight_unit = _cell(row, "Variant Weight Unit") or "GRAMS"
        taxable_raw = _cell(row, "Variant Taxable")
        inventory_qty_raw = _cell(row, "Variant Inventory Qty", "Inventory Qty")

        option_values = [
            {"optionName": name, "name": value} for name, value in option_defs
        ]
        # Always create a variant row when this CSV row has commerce fields or options
        has_variant_signal = bool(
            option_defs
            or price
            or sku
            or barcode
            or inventory_qty_raw
            or compare_at
            or product.source_rows == 1
        )
        if has_variant_signal:
            weight = None
            if grams:
                try:
                    weight = float(grams)
                except ValueError as exc:
                    raise CsvImportError(
                        f"Row {index}: invalid Variant Grams '{grams}'"
                    ) from exc
            inventory_qty = None
            if inventory_qty_raw:
                try:
                    inventory_qty = int(float(inventory_qty_raw))
                except ValueError as exc:
                    raise CsvImportError(
                        f"Row {index}: invalid Variant Inventory Qty "
                        f"'{inventory_qty_raw}'"
                    ) from exc
            taxable = _truthy(taxable_raw)
            product.variants.append(
                ParsedVariant(
                    option_values=option_values,
                    price=price or None,
                    compare_at_price=compare_at or None,
                    sku=sku or None,
                    barcode=barcode or None,
                    weight=weight,
                    weight_unit=weight_unit.upper() if weight is not None else None,
                    taxable=taxable,
                    inventory_qty=inventory_qty,
                )
            )

        image_src = _cell(row, "Image Src", "Image URL")
        if image_src and image_src not in product.image_urls:
            product.image_urls.append(image_src)

    if not products:
        raise CsvImportError("CSV has headers but no product rows.")

    # Ensure every product has at least one variant for productSet
    for product in products.values():
        if not product.variants:
            product.variants.append(ParsedVariant(option_values=[]))
        if not product.options and any(v.option_values for v in product.variants):
            # Reconstruct options from variants if needed
            collected: dict[str, list[str]] = {}
            for variant in product.variants:
                for ov in variant.option_values:
                    collected.setdefault(ov["optionName"], [])
                    if ov["name"] not in collected[ov["optionName"]]:
                        collected[ov["optionName"]].append(ov["name"])
            product.options = [
                {"name": name, "values": values} for name, values in collected.items()
            ]

    return [products[handle] for handle in order]


def product_to_set_input(product: ParsedProduct) -> dict[str, Any]:
    """Convert a parsed product into a ProductSetInput payload."""
    payload: dict[str, Any] = {
        "title": product.title,
        "handle": product.handle,
        "status": product.status,
    }
    if product.description_html:
        payload["descriptionHtml"] = product.description_html
    if product.vendor:
        payload["vendor"] = product.vendor
    if product.product_type:
        payload["productType"] = product.product_type
    if product.tags:
        payload["tags"] = product.tags
    if product.seo_title or product.seo_description:
        seo: dict[str, str] = {}
        if product.seo_title:
            seo["title"] = product.seo_title
        if product.seo_description:
            seo["description"] = product.seo_description
        payload["seo"] = seo

    if product.options:
        payload["productOptions"] = [
            {
                "name": option["name"],
                "values": [{"name": value} for value in option["values"]],
            }
            for option in product.options
        ]

    variants_payload: list[dict[str, Any]] = []
    for variant in product.variants:
        item: dict[str, Any] = {}
        if variant.option_values:
            item["optionValues"] = variant.option_values
        if variant.price is not None:
            item["price"] = variant.price
        if variant.compare_at_price is not None:
            item["compareAtPrice"] = variant.compare_at_price
        if variant.sku is not None:
            item["sku"] = variant.sku
        if variant.barcode is not None:
            item["barcode"] = variant.barcode
        if variant.taxable is not None:
            item["taxable"] = variant.taxable
        variants_payload.append(item)
    payload["variants"] = variants_payload

    if product.image_urls:
        payload["files"] = [{"originalSource": url} for url in product.image_urls]

    return payload


def parsed_product_summary(product: ParsedProduct) -> dict[str, Any]:
    return {
        "handle": product.handle,
        "title": product.title,
        "status": product.status,
        "variant_count": len(product.variants),
        "image_count": len(product.image_urls),
        "tags": product.tags,
        "product_type": product.product_type,
        "vendor": product.vendor,
        "source_rows": product.source_rows,
    }
