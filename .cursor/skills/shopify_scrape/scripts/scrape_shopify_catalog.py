#!/usr/bin/env python3
"""Scrape a public product catalog website into a Shopify product-import CSV.

Output columns match ``shopify/shopify_product_import_example.csv``.
Every product is forced to Status=unlisted and Published=false.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as htmlmod
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TEMPLATE_HEADERS: list[str] = [
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

PLACEHOLDER_IMAGE = (
    "https://cdn.shopify.com/s/files/1/0533/2089/files/"
    "placeholder-images-image_large.png"
)
USER_AGENT = "AlishiaBot-ShopifyScrape/1.0 (+https://github.com/Justwhittaker/Alishia-Bot)"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}


@dataclass
class Product:
    handle: str = ""
    title: str = ""
    body_html: str = ""
    vendor: str = ""
    product_category: str = ""
    product_type: str = ""
    tags: str = ""
    option1_name: str = "Title"
    option1_value: str = "Default Title"
    option2_name: str = ""
    option2_value: str = ""
    option3_name: str = ""
    option3_value: str = ""
    sku: str = ""
    grams: str = "0"
    inventory_qty: str = "0"
    price: str = "0.00"
    compare_at: str = ""
    barcode: str = ""
    images: list[str] = field(default_factory=list)
    image_alt: str = ""
    seo_title: str = ""
    seo_description: str = ""
    google_category: str = ""
    google_gender: str = ""
    google_age_group: str = ""
    google_mpn: str = ""
    google_condition: str = ""
    weight_unit: str = "g"
    cost: str = ""
    requires_shipping: str = "true"
    taxable: str = "false"  # no VAT / no tax on all Shopify CSVs going forward
    source_url: str = ""


@dataclass
class ScrapeReport:
    seed_url: str
    product_urls_found: int = 0
    products_scraped: int = 0
    rows_written: int = 0
    images_kept: int = 0
    images_replaced: int = 0
    warnings: list[str] = field(default_factory=list)


def log(message: str) -> None:
    print(message, flush=True)


def fetch(url: str, timeout: float = 15.0) -> tuple[int, str, bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,application/json,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
        return getattr(response, "status", 200) or 200, text, raw


def absolutize(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href.strip())


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value[:100] or "imported-product"


def money(value: Any) -> str:
    if value is None:
        return ""
    cleaned = re.sub(r"[^\d.,-]", "", str(value)).replace(",", "")
    if not cleaned:
        return ""
    try:
        amount = float(cleaned)
        if amount < 0:
            return ""
        return f"{amount:.2f}"
    except ValueError:
        return ""


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


def looks_like_product_url(url: str) -> bool:
    path = urllib.parse.urlparse(url).path.lower()
    if any(x in path for x in ("/cart", "/account", "/checkout", "/collections/", "/blogs/", "/pages/")):
        if "/products/" not in path and "/product/" not in path:
            return False
    return bool(
        re.search(r"/products?/[^/]+/?$", path)
        or re.search(r"/product/[^/]+/?$", path)
        or re.search(r"/shop/[^/]+/?$", path)
    )


def parse_sitemap_xml(text: str, report: ScrapeReport, source: str = "sitemap") -> list[str]:
    found: list[str] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        report.warnings.append(f"sitemap parse error: {source}")
        return found
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for loc in root.findall(".//sm:url/sm:loc", ns):
        if not loc.text:
            continue
        href = loc.text.strip()
        if looks_like_product_url(href) or "/product/" in href.lower():
            found.append(href)
    return found


def discover_from_local_sitemap(path: Path, report: ScrapeReport) -> list[str]:
    if not path.is_file():
        report.warnings.append(f"local sitemap missing: {path}")
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    found = parse_sitemap_xml(text, report, source=str(path))
    log(f"Local sitemap {path}: {len(found)} product URLs")
    return found


def discover_from_sitemaps(seed: str, report: ScrapeReport) -> list[str]:
    parsed = urllib.parse.urlparse(seed)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    # Prefer product sitemaps first; keep discovery timeouts short so bad maps don't hang the run.
    candidates = [
        absolutize(origin, "/product-sitemap.xml"),
        absolutize(origin, "/sitemap_products_1.xml"),
        absolutize(origin, "/wp-sitemap-posts-product-1.xml"),
        absolutize(origin, "/sitemap.xml"),
        absolutize(origin, "/sitemap_index.xml"),
    ]
    found: list[str] = []
    seen_maps: set[str] = set()

    def parse_sitemap(url: str, depth: int = 0) -> None:
        if url in seen_maps or depth > 2:
            return
        seen_maps.add(url)
        log(f"Trying sitemap: {url}")
        try:
            _, text, _ = fetch(url, timeout=8.0)
        except Exception as exc:  # noqa: BLE001
            report.warnings.append(f"sitemap miss {url}: {exc}")
            log(f"  miss: {exc}")
            return
        nested = []
        try:
            root = ET.fromstring(text)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            nested = [
                loc.text.strip()
                for loc in root.findall(".//sm:sitemap/sm:loc", ns)
                if loc.text
            ]
        except ET.ParseError:
            report.warnings.append(f"sitemap parse error: {url}")
            return
        for child in nested:
            parse_sitemap(child, depth + 1)
        urls = parse_sitemap_xml(text, report, source=url)
        log(f"  found {len(urls)} product URLs")
        found.extend(urls)

    for candidate in candidates:
        parse_sitemap(candidate)
        if found:
            break
    return found


def discover_from_html(seed: str, report: ScrapeReport) -> list[str]:
    urls = [seed]
    # Common listing pages
    parsed = urllib.parse.urlparse(seed)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    for path in ("/shop/", "/collections/all", "/products.json", "/collections/all/products.json"):
        urls.append(absolutize(origin, path))

    found: list[str] = []
    for url in urls:
        try:
            _, text, _ = fetch(url)
        except Exception as exc:  # noqa: BLE001
            report.warnings.append(f"list miss {url}: {exc}")
            continue
        # Shopify products.json
        if url.endswith(".json"):
            try:
                payload = json.loads(text)
                products = payload.get("products") or []
                for product in products:
                    handle = product.get("handle")
                    if handle:
                        found.append(absolutize(origin, f"/products/{handle}"))
                continue
            except json.JSONDecodeError:
                pass
        for href in re.findall(r'href=["\']([^"\']+)["\']', text, flags=re.I):
            abs_url = absolutize(url, href.split("#")[0])
            if looks_like_product_url(abs_url):
                found.append(abs_url)
    return found


def discover_product_urls(
    seed: str,
    limit: int,
    report: ScrapeReport,
    *,
    local_sitemap: Path | None = None,
    urls_file: Path | None = None,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    collected: list[str] = []
    if urls_file:
        if urls_file.is_file():
            collected.extend(
                line.strip()
                for line in urls_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            )
            log(f"Loaded {len(collected)} URLs from {urls_file}")
        else:
            report.warnings.append(f"urls file missing: {urls_file}")
    if local_sitemap:
        collected.extend(discover_from_local_sitemap(local_sitemap, report))
    if not collected:
        collected.extend(discover_from_sitemaps(seed, report))
    if len(collected) < limit:
        collected.extend(discover_from_html(seed, report))

    for href in collected:
        clean = href.split("?")[0].rstrip("/") + "/"
        key = clean.lower()
        if key in seen:
            continue
        if not looks_like_product_url(clean) and "/product" not in clean.lower():
            continue
        seen.add(key)
        ordered.append(clean)
        if len(ordered) >= limit:
            break
    report.product_urls_found = len(ordered)
    log(f"Discovery complete: {len(ordered)} product URLs (limit {limit})")
    return ordered


def extract_json_ld_products(html: str) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        types = node.get("@type")
        type_list = types if isinstance(types, list) else [types]
        if any(t in {"Product", "ProductGroup"} for t in type_list if t):
            products.append(node)
        if "@graph" in node:
            walk(node["@graph"])

    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    ):
        raw = block.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        walk(data)
    return products


def first_meta(html: str, *patterns: str) -> str:
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.I | re.S)
        if match:
            return htmlmod.unescape(match.group(1)).strip()
    return ""


def strip_tags(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = htmlmod.unescape(re.sub(r"\s+", " ", text)).strip()
    return text


def to_html_body(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "<p>Product details coming soon.</p>"
    if "<" in text and ">" in text:
        return text
    escaped = htmlmod.escape(text)
    parts = [p.strip() for p in re.split(r"\n\s*\n", escaped) if p.strip()]
    if not parts:
        return f"<p>{escaped}</p>"
    return "".join(f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in parts)


def validate_image(url: str, cache: dict[str, bool], report: ScrapeReport) -> bool:
    if url in cache:
        return cache[url]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        cache[url] = False
        return False
    headers = {"User-Agent": USER_AGENT, "Accept": "image/*,*/*;q=0.8"}
    ok = False
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        if method == "GET":
            request.add_header("Range", "bytes=0-2047")
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                status = getattr(response, "status", 200) or 200
                if status >= 400:
                    continue
                content_type = (response.headers.get("Content-Type") or "").lower()
                if content_type.startswith("text/html"):
                    continue
                data = response.read(2048) if method == "GET" else b""
                if data and data.lstrip().startswith((b"<!DOCTYPE", b"<html", b"{")):
                    continue
                if content_type.startswith("image/") or data.startswith(
                    (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF8", b"RIFF", b"BM")
                ):
                    ok = True
                    break
                path = parsed.path.lower()
                if any(path.endswith(ext) for ext in IMAGE_EXTS) and method == "GET":
                    ok = True
                    break
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405, 501}:
                continue
        except Exception:  # noqa: BLE001
            continue
    cache[url] = ok
    if not ok:
        report.warnings.append(f"bad image: {url}")
    return ok


def parse_product_page(
    url: str,
    html: str,
    *,
    vendor_default: str,
    used_handles: set[str],
    image_cache: dict[str, bool],
    report: ScrapeReport,
    validate_images: bool,
) -> Product:
    product = Product(source_url=url)
    ld_products = extract_json_ld_products(html)
    ld = ld_products[0] if ld_products else {}

    title = str(ld.get("name") or "") or first_meta(
        html,
        r'property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        r"<title>(.*?)</title>",
    )
    title = re.sub(r"\s+[|\-–].*$", "", title).strip() or "Imported Product"
    product.title = title

    handle_from_url = urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1]
    product.handle = unique_handle(handle_from_url or title, used_handles)

    description = str(ld.get("description") or "") or first_meta(
        html,
        r'property=["\']og:description["\']\s+content=["\']([^"\']+)["\']',
        r'name=["\']description["\']\s+content=["\']([^"\']+)["\']',
        r'itemprop=["\']description["\'][^>]*>(.*?)</div>',
    )
    product.body_html = to_html_body(description)
    product.seo_title = title[:70]
    product.seo_description = strip_tags(description)[:320] or "Imported product — review before publishing."

    brand = ld.get("brand")
    if isinstance(brand, dict):
        product.vendor = str(brand.get("name") or "") or vendor_default
    elif isinstance(brand, str) and brand.strip():
        product.vendor = brand.strip()
    else:
        product.vendor = vendor_default

    # category / type crumbs
    crumbs = re.findall(r'rel=["\']tag["\'][^>]*>([^<]+)', html, flags=re.I)
    if crumbs:
        product.product_type = crumbs[-1].strip()
        product.tags = ", ".join(dict.fromkeys(c.strip() for c in crumbs if c.strip()))
    product.product_category = first_meta(
        html,
        r'property=["\']product:category["\']\s+content=["\']([^"\']+)["\']',
    )

    offers = ld.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if isinstance(offers, dict):
        product.price = money(offers.get("price") or offers.get("lowPrice")) or "0.00"
        sku = offers.get("sku") or ld.get("sku")
        if sku:
            product.sku = str(sku)
        availability = str(offers.get("availability") or "")
        if "OutOfStock" in availability:
            product.inventory_qty = "0"
        else:
            product.inventory_qty = "1"
    if not product.price or product.price == "0.00":
        price_match = re.search(
            r'woocommerce-Price-amount[^>]*>.*?<bdi>(?:<span[^>]*>[^<]*</span>)?([^<]+)',
            html,
            flags=re.I | re.S,
        )
        if price_match:
            product.price = money(price_match.group(1)) or "0.00"
    if not product.sku:
        product.sku = f"IMP-{product.handle[:40].upper()}"

    # images
    images: list[str] = []
    image_field = ld.get("image")
    if isinstance(image_field, str):
        images.append(image_field)
    elif isinstance(image_field, list):
        for item in image_field:
            if isinstance(item, str):
                images.append(item)
            elif isinstance(item, dict) and item.get("url"):
                images.append(str(item["url"]))
    og = first_meta(html, r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']')
    if og:
        images.append(og)
    for src in re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, flags=re.I):
        abs_src = absolutize(url, src)
        path = urllib.parse.urlparse(abs_src).path.lower()
        if any(path.endswith(ext) for ext in IMAGE_EXTS) or "/uploads/" in path or "/files/" in path:
            images.append(abs_src)

    cleaned_images: list[str] = []
    for image in images:
        if image.startswith("//"):
            image = "https:" + image
        if image in cleaned_images:
            continue
        if validate_images:
            if validate_image(image, image_cache, report):
                cleaned_images.append(image)
                report.images_kept += 1
        else:
            cleaned_images.append(image)
            report.images_kept += 1
        if len(cleaned_images) >= 5:
            break
    if not cleaned_images:
        cleaned_images = [PLACEHOLDER_IMAGE]
        report.images_replaced += 1
    product.images = cleaned_images
    product.image_alt = title

    # Shopify storefront product JSON enrichment if available
    if "/products/" in url:
        json_url = url.rstrip("/") + ".json"
        try:
            _, text, _ = fetch(json_url)
            payload = json.loads(text).get("product") or {}
            if payload.get("title"):
                product.title = str(payload["title"])
            if payload.get("body_html"):
                product.body_html = str(payload["body_html"])
            if payload.get("vendor"):
                product.vendor = str(payload["vendor"])
            if payload.get("product_type"):
                product.product_type = str(payload["product_type"])
            if payload.get("tags"):
                tags = payload["tags"]
                product.tags = ", ".join(tags) if isinstance(tags, list) else str(tags)
            variants = payload.get("variants") or []
            if variants:
                variant = variants[0]
                product.price = money(variant.get("price")) or product.price
                product.compare_at = money(variant.get("compare_at_price"))
                product.sku = str(variant.get("sku") or product.sku)
                product.barcode = str(variant.get("barcode") or "")
                grams = variant.get("grams")
                if grams is not None:
                    product.grams = str(int(grams))
                product.requires_shipping = "true" if variant.get("requires_shipping", True) else "false"
                # Always no VAT / no tax on exported Shopify CSVs
                product.taxable = "false"
                options = payload.get("options") or []
                if options:
                    product.option1_name = str(options[0].get("name") or "Title")
                    product.option1_value = str(variant.get("option1") or "Default Title")
                    if len(options) > 1:
                        product.option2_name = str(options[1].get("name") or "")
                        product.option2_value = str(variant.get("option2") or "")
                    if len(options) > 2:
                        product.option3_name = str(options[2].get("name") or "")
                        product.option3_value = str(variant.get("option3") or "")
            images_json = payload.get("images") or []
            json_images = [str(img.get("src")) for img in images_json if img.get("src")]
            if json_images:
                product.images = []
                for image in json_images[:5]:
                    if validate_images and not validate_image(image, image_cache, report):
                        continue
                    product.images.append(image)
                    report.images_kept += 1
                if not product.images:
                    product.images = [PLACEHOLDER_IMAGE]
                    report.images_replaced += 1
        except Exception:  # noqa: BLE001
            pass

    if not product.product_type:
        product.product_type = "General"
    if product.source_url and "imported" not in product.tags.lower():
        product.tags = ", ".join(t for t in [product.tags, "imported", "unlisted"] if t)
    return product


def product_to_rows(product: Product) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    first = {h: "" for h in TEMPLATE_HEADERS}
    first.update(
        {
            "Handle": product.handle,
            "Title": product.title,
            "Body (HTML)": product.body_html,
            "Vendor": product.vendor,
            "Product Category": product.product_category or product.google_category,
            "Type": product.product_type,
            "Tags": product.tags,
            "Published": "false",
            "Status": "unlisted",
            "Option1 Name": product.option1_name or "Title",
            "Option1 Value": product.option1_value or "Default Title",
            "Option2 Name": product.option2_name,
            "Option2 Value": product.option2_value,
            "Option3 Name": product.option3_name,
            "Option3 Value": product.option3_value,
            "Variant SKU": product.sku,
            "Variant Grams": product.grams or "0",
            "Variant Inventory Tracker": "shopify",
            "Variant Inventory Qty": product.inventory_qty or "0",
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Price": product.price or "0.00",
            "Variant Compare At Price": product.compare_at,
            "Variant Requires Shipping": product.requires_shipping,
            "Variant Taxable": "false",  # always no VAT / no tax
            "Variant Barcode": product.barcode,
            "Image Src": product.images[0] if product.images else PLACEHOLDER_IMAGE,
            "Image Position": "1",
            "Image Alt Text": product.image_alt or product.title,
            "Gift Card": "false",
            "SEO Title": product.seo_title or product.title[:70],
            "SEO Description": product.seo_description,
            "Google Shopping / Google Product Category": product.google_category,
            "Google Shopping / Gender": product.google_gender,
            "Google Shopping / Age Group": product.google_age_group,
            "Google Shopping / MPN": product.google_mpn,
            "Google Shopping / Condition": product.google_condition,
            "Variant Weight Unit": product.weight_unit or "g",
            "Cost per item": product.cost,
            "Included / United States": "true",
            "Included / International": "true",
        }
    )
    rows.append(first)
    for index, image in enumerate(product.images[1:], start=2):
        extra = {h: "" for h in TEMPLATE_HEADERS}
        extra.update(
            {
                "Handle": product.handle,
                "Published": "false",
                "Status": "unlisted",
                "Image Src": image,
                "Image Position": str(index),
                "Image Alt Text": product.image_alt or product.title,
            }
        )
        rows.append(extra)
    return rows


def scrape(
    seed_url: str,
    output: Path,
    *,
    limit: int,
    vendor: str,
    delay: float,
    validate_images: bool,
    local_sitemap: Path | None = None,
    urls_file: Path | None = None,
) -> ScrapeReport:
    report = ScrapeReport(seed_url=seed_url)
    product_urls = discover_product_urls(
        seed_url,
        limit=limit,
        report=report,
        local_sitemap=local_sitemap,
        urls_file=urls_file,
    )
    if not product_urls:
        raise SystemExit(
            f"No product URLs discovered from {seed_url}. "
            "Try a shop/collection/sitemap URL, or pass --local-sitemap / --urls-file."
        )

    used_handles: set[str] = set()
    image_cache: dict[str, bool] = {}
    all_rows: list[dict[str, str]] = []

    for index, product_url in enumerate(product_urls, start=1):
        try:
            _, html, _ = fetch(product_url, timeout=25.0)
            product = parse_product_page(
                product_url,
                html,
                vendor_default=vendor,
                used_handles=used_handles,
                image_cache=image_cache,
                report=report,
                validate_images=validate_images,
            )
            rows = product_to_rows(product)
            all_rows.extend(rows)
            report.products_scraped += 1
            report.rows_written += len(rows)
            log(f"[{index}/{len(product_urls)}] {product.title} → {product.handle}")
        except Exception as exc:  # noqa: BLE001
            report.warnings.append(f"failed {product_url}: {exc}")
            print(f"[{index}/{len(product_urls)}] FAIL {product_url}: {exc}", file=sys.stderr, flush=True)
        if delay > 0 and index < len(product_urls):
            time.sleep(delay)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TEMPLATE_HEADERS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    meta_path = output.with_suffix(".meta.json")
    meta_path.write_text(
        json.dumps(
            {
                "seed_url": report.seed_url,
                "product_urls_found": report.product_urls_found,
                "products_scraped": report.products_scraped,
                "rows_written": report.rows_written,
                "images_kept": report.images_kept,
                "images_replaced": report.images_replaced,
                "output_csv": str(output),
                "warnings": report.warnings[:100],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape a website catalog into Shopify CSV template columns.")
    parser.add_argument("url", help="Website / shop / collection / sitemap URL to scrape")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("shopify/out/shopify_scrape_unlisted.csv"),
        help="Output CSV path",
    )
    parser.add_argument("--limit", type=int, default=200, help="Max products to scrape")
    parser.add_argument("--vendor", default="Imported Catalog", help="Default vendor")
    parser.add_argument("--delay", type=float, default=0.35, help="Delay between product fetches")
    parser.add_argument(
        "--local-sitemap",
        type=Path,
        default=None,
        help="Parse product URLs from a local sitemap XML file first",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        default=None,
        help="Text file with one product URL per line",
    )
    parser.add_argument(
        "--skip-image-validation",
        action="store_true",
        help="Skip HTTP image validation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = scrape(
        args.url,
        args.output,
        limit=args.limit,
        vendor=args.vendor,
        delay=args.delay,
        validate_images=not args.skip_image_validation,
        local_sitemap=args.local_sitemap,
        urls_file=args.urls_file,
    )
    log(f"Wrote {args.output}")
    log(
        f"URLs found: {report.product_urls_found} | scraped: {report.products_scraped} | rows: {report.rows_written}"
    )
    log(f"Images kept: {report.images_kept} | placeholder replacements: {report.images_replaced}")
    log("Status forced to unlisted; Published forced to false")
    if report.warnings:
        log(f"Warnings: {len(report.warnings)} (see {args.output.with_suffix('.meta.json')})")
    return 0 if report.products_scraped else 2


if __name__ == "__main__":
    raise SystemExit(main())
