#!/usr/bin/env python3
"""Convert source product CSVs into Shopify Admin product-import CSVs.

Hard rules:
- Output headers match shopify/shopify_product_import_example.csv
- Every product Status is forced to ``unlisted``
- Every product Published is forced to ``false``
- Missing/invalid fields get Shopify-safe placeholders
- Image URLs are validated; broken/non-image URLs are replaced
- Optional ``**...**`` custom edits (collections/tags/vendor/type) are applied
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


DEFAULT_TEMPLATE = Path("/workspace/shopify/shopify_product_import_example.csv")
# scripts/ → shopify-csv/ → skills/ → .cursor/ → repo root
REPO_TEMPLATE = Path(__file__).resolve().parents[4] / "shopify" / "shopify_product_import_example.csv"

# Fallback matches shopify/shopify_product_import_example.csv if the file is missing.
FALLBACK_SHOPIFY_HEADERS: list[str] = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Product Category",
    "Type",
    "Tags",
    "Published",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Option3 Name",
    "Option3 Value",
    "Variant SKU",
    "Variant Grams",
    "Variant Inventory Tracker",
    "Variant Inventory Qty",
    "Variant Inventory Policy",
    "Variant Fulfillment Service",
    "Variant Price",
    "Variant Compare At Price",
    "Variant Requires Shipping",
    "Variant Taxable",
    "Variant Barcode",
    "Image Src",
    "Image Position",
    "Image Alt Text",
    "Gift Card",
    "SEO Title",
    "SEO Description",
    "Google Shopping / Google Product Category",
    "Google Shopping / Gender",
    "Google Shopping / Age Group",
    "Google Shopping / MPN",
    "Google Shopping / Condition",
    "Google Shopping / Custom Product",
    "Google Shopping / Custom Label 0",
    "Google Shopping / Custom Label 1",
    "Google Shopping / Custom Label 2",
    "Google Shopping / Custom Label 3",
    "Google Shopping / Custom Label 4",
    "Variant Image",
    "Variant Weight Unit",
    "Variant Tax Code",
    "Cost per item",
    "Included / United States",
    "Included / International",
    "Price / International",
    "Compare At Price / International",
    "Status",
]

SHOPIFY_HEADERS: list[str] = list(FALLBACK_SHOPIFY_HEADERS)


def load_template_headers(template: Path | None = None) -> list[str]:
    """Load exact Shopify CSV headers from the gold-standard example file."""
    candidates = []
    if template is not None:
        candidates.append(template)
    candidates.extend([DEFAULT_TEMPLATE, REPO_TEMPLATE])
    for path in candidates:
        if path.is_file():
            with path.open(newline="", encoding="utf-8-sig") as handle:
                reader = csv.reader(handle)
                headers = next(reader)
            if not headers:
                raise SystemExit(f"No headers in template: {path}")
            return headers
    return list(FALLBACK_SHOPIFY_HEADERS)

# Shopify-safe placeholder image (public CDN sample asset).
PLACEHOLDER_IMAGE = (
    "https://cdn.shopify.com/s/files/1/0533/2089/files/"
    "placeholder-images-image_large.png"
)

DEFAULT_VENDOR = "Imported Catalog"
DEFAULT_TYPE = "General"
DEFAULT_PRICE = "0.00"
DEFAULT_GRAMS = "0"
DEFAULT_QTY = "0"
DEFAULT_OPTION_NAME = "Title"
DEFAULT_OPTION_VALUE = "Default Title"
DEFAULT_BODY = "<p>Product details coming soon.</p>"
DEFAULT_SEO_DESC = "Imported product — review before publishing."

# Scraped-column aliases → logical field
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "title": (
        "title",
        "name",
        "product_title",
        "product_name",
        "product",
        "surname",
        "business_name",
        "item",
        "item_name",
    ),
    "handle": ("handle", "slug", "url_handle", "product_handle", "seo_slug"),
    "body": (
        "body",
        "body_html",
        "description",
        "desc",
        "product_description",
        "about",
        "about_blurb",
        "details",
        "history_text",
        "short_description",
    ),
    "vendor": ("vendor", "brand", "manufacturer", "supplier", "store"),
    "type": ("type", "product_type", "category", "venue_category", "product category"),
    "tags": ("tags", "keywords", "labels"),
    "sku": ("sku", "variant_sku", "product_sku", "item_sku", "product_id", "id"),
    "price": (
        "price",
        "variant_price",
        "sale_price",
        "amount",
        "cost",
        "unit_price",
    ),
    "compare_at": (
        "compare_at",
        "compare_at_price",
        "variant_compare_at_price",
        "msrp",
        "rrp",
        "list_price",
    ),
    "barcode": ("barcode", "ean", "upc", "gtin", "isbn"),
    "grams": ("grams", "weight_grams", "variant_grams", "weight"),
    "weight_unit": ("weight_unit", "variant_weight_unit", "unit"),
    "qty": (
        "qty",
        "quantity",
        "inventory",
        "inventory_qty",
        "variant_inventory_qty",
        "stock",
    ),
    "image": (
        "image",
        "image_url",
        "image_src",
        "img",
        "photo",
        "thumbnail",
        "picture",
        "main_image",
        "product_image",
    ),
    "image_2": ("image_2", "image2", "secondary_image", "image_url_2"),
    "image_3": ("image_3", "image3", "image_url_3"),
    "image_alt": ("image_alt", "alt", "alt_text", "image_alt_text"),
    "url": ("url", "product_url", "source_url", "link", "canonical_url"),
    "option1_name": ("option1_name", "option1 name", "size_name"),
    "option1_value": ("option1_value", "option1 value", "size", "variant", "color"),
    "option2_name": ("option2_name", "option2 name"),
    "option2_value": ("option2_value", "option2 value"),
    "option3_name": ("option3_name", "option3 name"),
    "option3_value": ("option3_value", "option3 value"),
    "seo_title": ("seo_title", "meta_title"),
    "seo_description": ("seo_description", "meta_description"),
    "product_category": (
        "product_category",
        "google_category",
        "shopify_category",
        "taxonomy",
    ),
    "requires_shipping": ("requires_shipping", "shipping", "physical"),
    "taxable": ("taxable", "tax"),
    "cost": ("cost_per_item", "cost per item", "wholesale", "unit_cost"),
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
MIN_IMAGE_BYTES = 200

# Custom edits live in the user message as **directive + value lines**
CUSTOM_EDIT_BLOCK_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


@dataclass
class CustomEdit:
    directive: str
    values: list[str]


@dataclass
class ConvertReport:
    input_rows: int = 0
    output_rows: int = 0
    products: int = 0
    images_kept: int = 0
    images_replaced: int = 0
    placeholders_used: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    custom_edits_applied: list[str] = field(default_factory=list)

    def bump_placeholder(self, key: str) -> None:
        self.placeholders_used[key] = self.placeholders_used.get(key, 0) + 1


def parse_custom_edits(text: str) -> list[CustomEdit]:
    """Parse ``**directive\\nvalue\\nvalue **`` blocks from the user message."""
    if not text or not text.strip():
        return []
    edits: list[CustomEdit] = []
    for raw_block in CUSTOM_EDIT_BLOCK_RE.findall(text):
        lines = [ln.strip() for ln in raw_block.splitlines()]
        lines = [ln for ln in lines if ln]
        if not lines:
            continue
        directive = lines[0].strip().strip("*").strip()
        values = [ln.strip().strip("*").strip() for ln in lines[1:] if ln.strip().strip("*").strip()]
        if directive:
            edits.append(CustomEdit(directive=directive, values=values))
    return edits


def merge_tags(existing: str, additions: Iterable[str]) -> str:
    seen: list[str] = []
    for part in re.split(r"\s*,\s*", (existing or "").strip()):
        if part and part not in seen:
            seen.append(part)
    for item in additions:
        tag = (item or "").strip()
        if tag and tag not in seen:
            seen.append(tag)
    return ", ".join(seen)


def apply_custom_edits(
    rows: list[dict[str, str]],
    edits: list[CustomEdit],
    report: ConvertReport,
) -> list[dict[str, str]]:
    if not edits:
        return rows

    for edit in edits:
        directive = edit.directive.lower().strip()
        values = [v for v in edit.values if v]

        if directive in {"add collections to all items", "add collection to all items"}:
            if not values:
                report.warnings.append(f"Custom edit '{edit.directive}' had no collection names")
                continue
            for row in rows:
                # Product rows and image-only rows both get tags so Admin stays consistent.
                row["Tags"] = merge_tags(row.get("Tags", ""), values)
            report.custom_edits_applied.append(
                f"add collections to all items → {', '.join(values)}"
            )
            continue

        if directive in {"add tags to all items", "add tag to all items"}:
            if not values:
                report.warnings.append(f"Custom edit '{edit.directive}' had no tags")
                continue
            for row in rows:
                row["Tags"] = merge_tags(row.get("Tags", ""), values)
            report.custom_edits_applied.append(f"add tags to all items → {', '.join(values)}")
            continue

        if directive in {"set vendor", "vendor"}:
            if not values:
                report.warnings.append(f"Custom edit '{edit.directive}' had no vendor value")
                continue
            vendor = values[0]
            for row in rows:
                if (row.get("Title") or "").strip():
                    row["Vendor"] = vendor
            report.custom_edits_applied.append(f"set vendor → {vendor}")
            continue

        if directive in {"set type", "type", "set product type"}:
            if not values:
                report.warnings.append(f"Custom edit '{edit.directive}' had no type value")
                continue
            product_type = values[0]
            for row in rows:
                if (row.get("Title") or "").strip():
                    row["Type"] = product_type
            report.custom_edits_applied.append(f"set type → {product_type}")
            continue

        report.warnings.append(f"Unknown custom edit directive (skipped): {edit.directive}")

    return rows


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def build_header_map(headers: Iterable[str]) -> dict[str, str]:
    """Map logical field → actual CSV header present in the file."""
    norm_to_actual = {normalize_key(h): h for h in headers if h}
    mapping: dict[str, str] = {}
    for logical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            actual = norm_to_actual.get(normalize_key(alias))
            if actual:
                mapping[logical] = actual
                break
    return mapping


def cell(row: dict[str, str], header_map: dict[str, str], logical: str) -> str:
    header = header_map.get(logical)
    if not header:
        return ""
    return (row.get(header) or "").strip()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:100] or "imported-product"


def title_case_slug(slug: str) -> str:
    parts = [p for p in re.split(r"[-_\s]+", slug) if p]
    if not parts:
        return "Imported Product"
    titled = " ".join(p[:1].upper() + p[1:] for p in parts)
    if titled.lower().startswith("mc") and len(titled) > 2 and titled[2:3].islower():
        titled = "Mc" + titled[2:3].upper() + titled[3:]
    return titled


def to_html_body(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if "<" in text and ">" in text:
        return text
    escaped = html.escape(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", escaped) if p.strip()]
    if not paragraphs:
        return f"<p>{escaped}</p>"
    return "".join(f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in paragraphs)


def money(value: str, fallback: str, report: ConvertReport, key: str) -> str:
    raw = (value or "").strip()
    if not raw:
        report.bump_placeholder(key)
        return fallback
    cleaned = re.sub(r"[^\d.,-]", "", raw).replace(",", "")
    try:
        amount = float(cleaned)
        if amount < 0:
            raise ValueError("negative")
        return f"{amount:.2f}"
    except ValueError:
        report.bump_placeholder(key)
        report.warnings.append(f"Invalid price '{value}' → {fallback}")
        return fallback


def int_string(value: str, fallback: str, report: ConvertReport, key: str) -> str:
    raw = (value or "").strip()
    if not raw:
        report.bump_placeholder(key)
        return fallback
    cleaned = re.sub(r"[^\d.-]", "", raw)
    try:
        number = int(float(cleaned))
        if number < 0:
            raise ValueError("negative")
        return str(number)
    except ValueError:
        report.bump_placeholder(key)
        return fallback


def looks_like_image_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return True
    # CDN/media paths without extension still allowed for validation step
    return any(token in path for token in ("/image", "/images", "/media", "/uploads", "/files"))


def validate_image_url(url: str, timeout: float = 8.0) -> tuple[bool, str]:
    """Return (ok, reason). Rejects HTML error pages and tiny non-image payloads."""
    if not looks_like_image_url(url):
        return False, "not an http(s) image URL"

    headers = {
        "User-Agent": "AlishiaBot-ShopifyCSV/1.0 (+https://github.com/Justwhittaker/Alishia-Bot)",
        "Accept": "image/*,*/*;q=0.8",
    }

    # Prefer HEAD; fall back to ranged GET
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        if method == "GET":
            request.add_header("Range", "bytes=0-2047")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200) or 200
                if status >= 400:
                    return False, f"HTTP {status}"
                content_type = (response.headers.get("Content-Type") or "").lower()
                if content_type.startswith("text/html"):
                    return False, "HTML response (not an image)"
                if content_type and not (
                    content_type.startswith("image/")
                    or content_type in {"application/octet-stream", "binary/octet-stream"}
                ):
                    # Some CDNs omit useful types; still peek body on GET
                    if method == "HEAD":
                        continue
                data = b""
                if method == "GET":
                    data = response.read(2048)
                    if data.lstrip().startswith((b"<!DOCTYPE", b"<html", b"{", b"[")):
                        return False, "body looks like HTML/JSON, not image"
                    if len(data) < 32 and not content_type.startswith("image/"):
                        return False, "payload too small"
                # Magic-byte sniff when we have bytes
                if data:
                    if not (
                        data.startswith(b"\xff\xd8\xff")  # jpeg
                        or data.startswith(b"\x89PNG\r\n\x1a\n")  # png
                        or data.startswith(b"GIF87a")
                        or data.startswith(b"GIF89a")
                        or data.startswith(b"RIFF")  # webp/wav container
                        or data.startswith(b"BM")
                        or content_type.startswith("image/")
                    ):
                        return False, "unrecognized image signature"
                if content_type.startswith("image/") or data:
                    return True, "ok"
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405, 501}:
                continue
            return False, f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - network edge cases
            if method == "HEAD":
                continue
            return False, str(exc)[:120]
    return False, "unreachable"


def pick_image(
    candidates: list[str],
    *,
    validate: bool,
    report: ConvertReport,
    cache: dict[str, tuple[bool, str]],
) -> str:
    for raw in candidates:
        url = (raw or "").strip()
        if not url:
            continue
        if url.startswith("//"):
            url = "https:" + url
        if not validate:
            report.images_kept += 1
            return url
        if url not in cache:
            cache[url] = validate_image_url(url)
        ok, reason = cache[url]
        if ok:
            report.images_kept += 1
            return url
        report.warnings.append(f"Dropped image ({reason}): {url}")
    report.images_replaced += 1
    report.bump_placeholder("image")
    return PLACEHOLDER_IMAGE


def unique_handle(base: str, used: set[str]) -> str:
    handle = slugify(base)
    if handle not in used:
        used.add(handle)
        return handle
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:6]
    candidate = f"{handle}-{digest}"
    n = 2
    while candidate in used:
        candidate = f"{handle}-{digest}-{n}"
        n += 1
    used.add(candidate)
    return candidate


def blank_shopify_row(headers: list[str] | None = None) -> dict[str, str]:
    return {h: "" for h in (headers or SHOPIFY_HEADERS)}


def convert_rows(
    scraped_rows: list[dict[str, str]],
    headers: list[str],
    *,
    vendor_default: str,
    validate_images: bool,
    report: ConvertReport,
) -> list[dict[str, str]]:
    header_map = build_header_map(headers)
    if "title" not in header_map and "handle" not in header_map and "url" not in header_map:
        report.warnings.append(
            "No title/handle/url column detected — every row will use placeholders."
        )

    used_handles: set[str] = set()
    image_cache: dict[str, tuple[bool, str]] = {}
    out: list[dict[str, str]] = []

    for index, scraped in enumerate(scraped_rows, start=1):
        report.input_rows += 1
        title = cell(scraped, header_map, "title")
        handle_src = cell(scraped, header_map, "handle")
        url = cell(scraped, header_map, "url")

        if not title and handle_src:
            title = title_case_slug(handle_src)
            report.bump_placeholder("title_from_handle")
        if not title and url:
            slug = urlparse(url).path.rstrip("/").split("/")[-1]
            title = title_case_slug(slug) if slug else ""
            if title:
                report.bump_placeholder("title_from_url")
        if not title:
            title = f"Imported Product {index}"
            report.bump_placeholder("title")

        handle_base = handle_src or slugify(title) or f"imported-product-{index}"
        handle = unique_handle(handle_base, used_handles)

        body_raw = cell(scraped, header_map, "body")
        body = to_html_body(body_raw) if body_raw else ""
        if not body:
            body = DEFAULT_BODY
            report.bump_placeholder("body")

        vendor = cell(scraped, header_map, "vendor") or vendor_default
        if not cell(scraped, header_map, "vendor"):
            report.bump_placeholder("vendor")

        product_type = cell(scraped, header_map, "type") or DEFAULT_TYPE
        if not cell(scraped, header_map, "type"):
            report.bump_placeholder("type")

        tags = cell(scraped, header_map, "tags")
        if url and "source" not in tags.lower():
            tags = ", ".join(t for t in [tags, "imported", "unlisted"] if t)

        sku = cell(scraped, header_map, "sku")
        if not sku:
            sku = f"IMP-{handle[:40].upper()}"
            report.bump_placeholder("sku")

        price = money(cell(scraped, header_map, "price"), DEFAULT_PRICE, report, "price")
        compare_at = cell(scraped, header_map, "compare_at")
        compare_at_value = ""
        if compare_at:
            compare_at_value = money(compare_at, "", report, "compare_at")

        grams = int_string(cell(scraped, header_map, "grams"), DEFAULT_GRAMS, report, "grams")
        qty = int_string(cell(scraped, header_map, "qty"), DEFAULT_QTY, report, "qty")
        weight_unit = cell(scraped, header_map, "weight_unit") or "g"

        option1_name = cell(scraped, header_map, "option1_name") or DEFAULT_OPTION_NAME
        option1_value = cell(scraped, header_map, "option1_value") or DEFAULT_OPTION_VALUE
        option2_name = cell(scraped, header_map, "option2_name")
        option2_value = cell(scraped, header_map, "option2_value")
        option3_name = cell(scraped, header_map, "option3_name")
        option3_value = cell(scraped, header_map, "option3_value")

        image_candidates = [
            cell(scraped, header_map, "image"),
            cell(scraped, header_map, "image_2"),
            cell(scraped, header_map, "image_3"),
        ]
        # Also accept any extra columns that look like image URLs
        for key, value in scraped.items():
            nk = normalize_key(key)
            if "image" in nk or nk in {"img", "photo", "thumbnail"}:
                if value and value.strip() not in image_candidates:
                    image_candidates.append(value.strip())

        primary_image = pick_image(
            image_candidates,
            validate=validate_images,
            report=report,
            cache=image_cache,
        )
        image_alt = cell(scraped, header_map, "image_alt") or title

        seo_title = cell(scraped, header_map, "seo_title") or title[:70]
        seo_description = cell(scraped, header_map, "seo_description") or DEFAULT_SEO_DESC
        if not cell(scraped, header_map, "seo_description"):
            report.bump_placeholder("seo_description")

        product_category = cell(scraped, header_map, "product_category")
        barcode = cell(scraped, header_map, "barcode")
        cost = cell(scraped, header_map, "cost")
        cost_value = money(cost, "", report, "cost") if cost else ""

        requires_shipping_raw = cell(scraped, header_map, "requires_shipping").lower()
        if requires_shipping_raw in {"false", "0", "no", "digital"}:
            requires_shipping = "false"
        else:
            requires_shipping = "true"

        taxable_raw = cell(scraped, header_map, "taxable").lower()
        taxable = "false" if taxable_raw in {"false", "0", "no"} else "true"

        row = blank_shopify_row()
        row.update(
            {
                "Handle": handle,
                "Title": title,
                "Body (HTML)": body,
                "Vendor": vendor,
                "Product Category": product_category,
                "Type": product_type,
                "Tags": tags,
                # CRITICAL: always unlisted / not published to Online Store
                "Published": "false",
                "Status": "unlisted",
                "Option1 Name": option1_name,
                "Option1 Value": option1_value,
                "Option2 Name": option2_name,
                "Option2 Value": option2_value,
                "Option3 Name": option3_name,
                "Option3 Value": option3_value,
                "Variant SKU": sku,
                "Variant Grams": grams,
                "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": qty,
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": price,
                "Variant Compare At Price": compare_at_value,
                "Variant Requires Shipping": requires_shipping,
                "Variant Taxable": taxable,
                "Variant Barcode": barcode,
                "Image Src": primary_image,
                "Image Position": "1",
                "Image Alt Text": image_alt,
                "Gift Card": "false",
                "SEO Title": seo_title,
                "SEO Description": seo_description,
                "Variant Weight Unit": weight_unit if weight_unit in {"g", "kg", "lb", "oz"} else "g",
                "Cost per item": cost_value,
            }
        )
        out.append(row)
        report.products += 1
        report.output_rows += 1

        # Extra image rows (same Handle, blank Title) for additional valid images
        extra_images = image_candidates[1:]
        position = 2
        for extra in extra_images:
            candidate = (extra or "").strip()
            if not candidate or candidate == primary_image:
                continue
            if candidate.startswith("//"):
                candidate = "https:" + candidate
            if validate_images:
                if candidate not in image_cache:
                    image_cache[candidate] = validate_image_url(candidate)
                ok, reason = image_cache[candidate]
                if not ok:
                    report.warnings.append(f"Skipped extra image ({reason}): {candidate}")
                    continue
            img_row = blank_shopify_row()
            img_row["Handle"] = handle
            img_row["Image Src"] = candidate
            img_row["Image Position"] = str(position)
            img_row["Image Alt Text"] = image_alt
            # Keep unlisted markers even on image-only rows for safety
            img_row["Published"] = "false"
            img_row["Status"] = "unlisted"
            out.append(img_row)
            report.images_kept += 1
            report.output_rows += 1
            position += 1

    return out


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"No headers found in {path}")
        headers = list(reader.fieldnames)
        rows = [dict(row) for row in reader]
    return headers, rows


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
    headers: list[str] | None = None,
) -> None:
    fieldnames = headers or SHOPIFY_HEADERS
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def print_report(report: ConvertReport, output: Path) -> None:
    print(f"Wrote {output}")
    print(f"Products: {report.products}")
    print(f"Input rows: {report.input_rows} → Output rows: {report.output_rows}")
    print(f"Images kept: {report.images_kept} | replaced w/ placeholder: {report.images_replaced}")
    if report.placeholders_used:
        print("Placeholders used:")
        for key, count in sorted(report.placeholders_used.items()):
            print(f"  - {key}: {count}")
    if report.custom_edits_applied:
        print("Custom edits applied:")
        for item in report.custom_edits_applied:
            print(f"  - {item}")
    if report.warnings:
        print(f"Warnings ({len(report.warnings)}):")
        for warning in report.warnings[:40]:
            print(f"  - {warning}")
        if len(report.warnings) > 40:
            print(f"  … {len(report.warnings) - 40} more")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a source CSV into a Shopify product-import CSV matching "
            "shopify_product_import_example.csv (always unlisted)."
        )
    )
    parser.add_argument(
        "input_csv",
        type=Path,
        help="Required path to the source CSV (<csv file path>)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output Shopify CSV path (default: shopify/out/<stem>_shopify_unlisted.csv)",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Gold-standard Shopify CSV used for exact output headers",
    )
    parser.add_argument(
        "--edits",
        default="",
        help="Raw **...** custom-edit text from the user message",
    )
    parser.add_argument(
        "--edits-file",
        type=Path,
        default=None,
        help="File containing **...** custom-edit text",
    )
    parser.add_argument(
        "--vendor",
        default=DEFAULT_VENDOR,
        help=f"Default vendor when missing (default: {DEFAULT_VENDOR})",
    )
    parser.add_argument(
        "--skip-image-validation",
        action="store_true",
        help="Do not HTTP-validate image URLs (faster; still replaces empty images)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    global SHOPIFY_HEADERS

    args = parse_args(argv)
    input_csv: Path = args.input_csv
    if not input_csv.is_file():
        print(f"Input not found: {input_csv}", file=sys.stderr)
        print("Usage: /shopify_csv <csv file path>  then optional **custom edits**", file=sys.stderr)
        return 1

    template_headers = load_template_headers(args.template)
    SHOPIFY_HEADERS = list(template_headers)

    output = args.output
    if output is None:
        out_dir = Path("/workspace/shopify/out")
        if not out_dir.parent.is_dir():
            out_dir = Path("shopify/out")
        output = out_dir / f"{input_csv.stem}_shopify_unlisted.csv"

    edits_text = args.edits or ""
    if args.edits_file is not None:
        if not args.edits_file.is_file():
            print(f"Edits file not found: {args.edits_file}", file=sys.stderr)
            return 1
        edits_text = args.edits_file.read_text(encoding="utf-8")

    custom_edits = parse_custom_edits(edits_text)

    headers, scraped_rows = read_csv(input_csv)
    report = ConvertReport()
    shopify_rows = convert_rows(
        scraped_rows,
        headers,
        vendor_default=args.vendor,
        validate_images=not args.skip_image_validation,
        report=report,
    )
    shopify_rows = apply_custom_edits(shopify_rows, custom_edits, report)
    write_csv(output, shopify_rows, headers=SHOPIFY_HEADERS)
    print_report(report, output)
    print(f"Template headers: {len(SHOPIFY_HEADERS)} columns from example CSV")
    print("Status column forced to: unlisted")
    print("Published column forced to: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
