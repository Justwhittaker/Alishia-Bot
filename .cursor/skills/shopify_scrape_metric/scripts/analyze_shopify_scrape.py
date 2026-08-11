#!/usr/bin/env python3
"""Analyze a Shopify-template scrape CSV for present vs missing field coverage."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PLACEHOLDER_MARKERS: dict[str, tuple[str, ...]] = {
    "Body (HTML)": ("product details coming soon",),
    "Type": ("general",),
    "Variant Price": ("0.00",),
    "Variant Grams": ("0",),
    "Variant Inventory Qty": ("0",),
    "SEO Description": ("imported product — review before publishing", "imported product - review before publishing"),
    "Image Src": ("placeholder-images",),
    "Vendor": ("imported catalog",),
}


def is_present(value: str) -> bool:
    return bool((value or "").strip())


def is_placeholder(column: str, value: str) -> bool:
    lowered = (value or "").strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS.get(column, ()))


def analyze(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"No rows in {path}")

    columns = list(rows[0].keys())
    product_rows = [r for r in rows if (r.get("Title") or "").strip()]

    def has_variant_price(row: dict[str, str]) -> bool:
        return bool((row.get("Variant Price") or "").strip())

    # Variant continuation rows: no Title, but priced (extra SKUs/options)
    variant_extra_rows = [
        r
        for r in rows
        if not (r.get("Title") or "").strip() and has_variant_price(r)
    ]
    # Any row that carries a selling price is a variant (includes product row)
    variant_priced_rows = [r for r in rows if has_variant_price(r)]
    image_only_rows = [
        r
        for r in rows
        if not (r.get("Title") or "").strip()
        and not has_variant_price(r)
        and (r.get("Image Src") or "").strip()
    ]
    # Backward-compatible alias used in older summaries
    variant_rows = variant_extra_rows

    handles = {(r.get("Handle") or "").strip() for r in rows if (r.get("Handle") or "").strip()}
    variants_per_handle: Counter[str] = Counter()
    for r in variant_priced_rows:
        h = (r.get("Handle") or "").strip()
        if h:
            variants_per_handle[h] += 1
    multi_variant_products = sum(1 for _h, count in variants_per_handle.items() if count > 1)
    single_variant_products = sum(1 for _h, count in variants_per_handle.items() if count == 1)
    max_variants = max(variants_per_handle.values()) if variants_per_handle else 0
    avg_variants = (
        round(sum(variants_per_handle.values()) / len(variants_per_handle), 2)
        if variants_per_handle
        else 0.0
    )
    top_multi = [
        {"handle": handle, "variants": count}
        for handle, count in variants_per_handle.most_common(15)
        if count > 1
    ]

    categories = sorted(
        {
            (r.get("Product Category") or r.get("Type") or "").strip()
            for r in product_rows
            if (r.get("Product Category") or r.get("Type") or "").strip()
        }
    )
    category_counts = Counter(
        (r.get("Product Category") or r.get("Type") or "Uncategorized").strip() or "Uncategorized"
        for r in product_rows
    )

    # Field coverage measured on product rows (first row per product) for product-level
    # fields, and on all variant-priced rows for variant fields.
    product_level = {
        "Handle",
        "Title",
        "Body (HTML)",
        "Vendor",
        "Product Category",
        "Type",
        "Tags",
        "Published",
        "Status",
        "Gift Card",
        "SEO Title",
        "SEO Description",
        "Google Shopping / Google Product Category",
        "Google Shopping / Gender",
        "Google Shopping / Age Group",
        "Google Shopping / MPN",
        "Google Shopping / Condition",
        "Included / United States",
        "Included / International",
    }

    variant_level = {
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
        "Variant Image",
        "Variant Weight Unit",
        "Variant Tax Code",
        "Cost per item",
        "Price / International",
        "Compare At Price / International",
    }

    fields: list[dict[str, Any]] = []
    for column in columns:
        if column in product_level:
            sample = product_rows
        elif column.startswith("Image ") or column == "Image Src":
            sample = rows
        elif column in variant_level:
            sample = variant_priced_rows or product_rows
        else:
            sample = product_rows
        total = len(sample) or len(rows)
        present = 0
        missing = 0
        placeholder = 0
        real = 0
        for row in sample:
            value = row.get(column, "")
            if not is_present(value):
                missing += 1
                continue
            present += 1
            if is_placeholder(column, value):
                placeholder += 1
            else:
                real += 1
        fields.append(
            {
                "field": column,
                "total": total,
                "present": present,
                "missing": missing,
                "real": real,
                "placeholder": placeholder,
                "presentPct": round(100 * present / total, 1) if total else 0.0,
                "missingPct": round(100 * missing / total, 1) if total else 0.0,
                "realPct": round(100 * real / total, 1) if total else 0.0,
                "placeholderPct": round(100 * placeholder / total, 1) if total else 0.0,
            }
        )

    fields_sorted = sorted(fields, key=lambda item: (-item["missingPct"], item["field"]))
    missing_fields = [f for f in fields if f["missing"] > 0]
    complete_fields = [f for f in fields if f["missing"] == 0 and f["placeholder"] == 0]
    placeholder_fields = [f for f in fields if f["placeholder"] > 0]

    status_values = Counter((r.get("Status") or "").strip().lower() for r in product_rows)
    published_values = Counter((r.get("Published") or "").strip().lower() for r in product_rows)
    taxable_values = Counter(
        (r.get("Variant Taxable") or "").strip().lower() for r in variant_priced_rows
    )

    report = {
        "sourceCsv": str(path),
        "summary": {
            "totalRows": len(rows),
            "products": len(handles) if handles else len(product_rows),
            "productRows": len(product_rows),
            "variants": len(variant_priced_rows),
            "variantRows": len(variant_rows),
            "variantExtraRows": len(variant_extra_rows),
            "multiVariantProducts": multi_variant_products,
            "singleVariantProducts": single_variant_products,
            "avgVariantsPerProduct": avg_variants,
            "maxVariantsOnProduct": max_variants,
            "imageOnlyRows": len(image_only_rows),
            "categories": len(categories),
            "fieldsTracked": len(columns),
            "fieldsFullyPresent": len([f for f in fields if f["missing"] == 0]),
            "fieldsWithMissing": len(missing_fields),
            "fieldsWithPlaceholders": len(placeholder_fields),
            "fieldsCompleteReal": len(complete_fields),
            "unlistedProducts": status_values.get("unlisted", 0),
            "publishedFalse": published_values.get("false", 0),
            "taxableFalse": taxable_values.get("false", 0),
        },
        "variants": {
            "total": len(variant_priced_rows),
            "extraRows": len(variant_extra_rows),
            "multiVariantProducts": multi_variant_products,
            "singleVariantProducts": single_variant_products,
            "avgPerProduct": avg_variants,
            "maxOnProduct": max_variants,
            "topMultiVariant": top_multi,
        },
        "categories": [
            {"category": name, "products": count, "pct": round(100 * count / max(len(product_rows), 1), 1)}
            for name, count in category_counts.most_common()
        ],
        "fields": fields_sorted,
        "topMissing": fields_sorted[:15],
        "statusCounts": dict(status_values),
        "publishedCounts": dict(published_values),
        "taxableCounts": dict(taxable_values),
    }
    return report


def write_canvas(report: dict[str, Any], canvas_path: Path) -> None:
    payload = json.dumps(report, indent=2)
    canvas_path.parent.mkdir(parents=True, exist_ok=True)
    canvas_path.write_text(
        f'''/**
 * Shopify scrape metrics sanity check.
 * Auto-generated by /shopify_scrape_metric — do not hand-edit REPORT.
 */
import {{ Divider, Grid, H1, H2, Stack, Stat, Table, Text }} from "cursor/canvas";

const REPORT = {payload} as const;

export default function ShopifyScrapeMetrics() {{
  const s = REPORT.summary;
  const fieldRows = REPORT.fields.map((f) => [
    f.field,
    String(f.present),
    String(f.missing),
    `${{f.presentPct}}%`,
    `${{f.missingPct}}%`,
    `${{f.realPct}}%`,
    `${{f.placeholderPct}}%`,
  ]);
  const categoryRows = REPORT.categories.map((c) => [
    c.category,
    String(c.products),
    `${{c.pct}}%`,
  ]);
  const missingRows = REPORT.topMissing.map((f) => [
    f.field,
    `${{f.missingPct}}%`,
    String(f.missing),
    String(f.present),
    `${{f.placeholderPct}}% placeholder`,
  ]);

  return (
    <Stack gap={{20}} style={{{{ padding: 20 }}}}>
      <H1>Shopify scrape metrics</H1>
      <Text tone="secondary">Source: {{REPORT.sourceCsv}}</Text>

      <Grid columns={{4}} gap={{12}}>
        <Stat value={{String(s.products)}} label="Products" />
        <Stat value={{String(s.variants ?? s.variantRows)}} label="Variants" />
        <Stat value={{String(s.multiVariantProducts ?? 0)}} label="Multi-variant products" />
        <Stat value={{String(s.unlistedProducts)}} label="Unlisted products" />
      </Grid>

      <Grid columns={{4}} gap={{12}}>
        <Stat value={{String(s.categories)}} label="Categories" />
        <Stat value={{String(s.fieldsWithMissing)}} label="Fields with missing" />
        <Stat value={{String(s.avgVariantsPerProduct ?? 0)}} label="Avg variants / product" />
        <Stat value={{String(s.taxableFalse ?? 0)}} label="Taxable=false rows" />
      </Grid>

      <Text>
        Rows {{s.totalRows}} · product {{s.productRows}} · variant extras {{s.variantExtraRows ?? s.variantRows}} ·
        image-only {{s.imageOnlyRows}} · Published=false {{s.publishedFalse}} · fields tracked {{s.fieldsTracked}} ·
        placeholder fields {{s.fieldsWithPlaceholders}}
      </Text>

      <Divider />
      <H2>Top multi-variant products</H2>
      <Table
        headers={{["Handle", "Variants"]}}
        rows={{(REPORT.variants?.topMultiVariant ?? []).map((v) => [v.handle, String(v.variants)])}}
      />

      <Divider />
      <H2>Categories</H2>
      <Table headers={{["Category", "Products", "Share"]}} rows={{categoryRows}} />

      <Divider />
      <H2>Top missing fields</H2>
      <Table
        headers={{["Field", "Missing %", "Missing", "Present", "Note"]}}
        rows={{missingRows}}
      />

      <Divider />
      <H2>All fields — present vs missing</H2>
      <Table
        headers={{["Field", "Present", "Missing", "Present %", "Missing %", "Real %", "Placeholder %"]}}
        rows={{fieldRows}}
      />
    </Stack>
  );
}}
''',
        encoding="utf-8",
    )


def write_html(report: dict[str, Any], html_path: Path) -> None:
    """Self-contained HTML sanity table (always viewable even if canvas MCP is unavailable)."""
    s = report["summary"]
    cat_rows = "".join(
        f"<tr><td>{c['category']}</td><td>{c['products']}</td><td>{c['pct']}%</td></tr>"
        for c in report["categories"]
    )
    field_rows = "".join(
        (
            "<tr>"
            f"<td>{f['field']}</td>"
            f"<td>{f['present']}</td><td>{f['missing']}</td>"
            f"<td>{f['presentPct']}%</td><td>{f['missingPct']}%</td>"
            f"<td>{f['realPct']}%</td><td>{f['placeholderPct']}%</td>"
            "</tr>"
        )
        for f in report["fields"]
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(
        f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Shopify scrape metrics</title>
<style>
body{{font-family:ui-sans-serif,system-ui,sans-serif;margin:24px;background:#f6f3ee;color:#1c1917}}
h1{{color:#0f4c3a}} table{{border-collapse:collapse;width:100%;background:#fff;margin:12px 0 28px}}
th,td{{border:1px solid #e7e5e4;padding:8px 10px;text-align:left;font-size:14px}}
th{{background:#0f4c3a;color:#fff}} .stats span{{display:inline-block;background:#fff;border:1px solid #e7e5e4;border-radius:10px;padding:10px 14px;margin:4px 8px 4px 0}}
.muted{{color:#78716c}}
</style></head><body>
<h1>Shopify scrape metrics</h1>
<p class="muted">{report['sourceCsv']}</p>
<div class="stats">
<span><b>{s['products']}</b><br/>Products</span>
<span><b>{s.get('variants', s.get('variantRows', 0))}</b><br/>Variants</span>
<span><b>{s.get('multiVariantProducts', 0)}</b><br/>Multi-variant</span>
<span><b>{s['unlistedProducts']}</b><br/>Unlisted</span>
<span><b>{s['categories']}</b><br/>Categories</span>
<span><b>{s['fieldsWithMissing']}</b><br/>Fields with missing</span>
</div>
<p>Rows {s['totalRows']} · product {s['productRows']} · variant extras {s.get('variantExtraRows', s.get('variantRows', 0))} · image-only {s['imageOnlyRows']} · avg variants {s.get('avgVariantsPerProduct', 0)} · Published=false {s['publishedFalse']} · Taxable=false {s.get('taxableFalse', 0)}</p>
<h2>Top multi-variant products</h2>
<table><thead><tr><th>Handle</th><th>Variants</th></tr></thead><tbody>
{''.join(f"<tr><td>{v['handle']}</td><td>{v['variants']}</td></tr>" for v in report.get('variants', {}).get('topMultiVariant', []))}
</tbody></table>
<h2>Categories</h2>
<table><thead><tr><th>Category</th><th>Products</th><th>Share</th></tr></thead><tbody>{cat_rows}</tbody></table>
<h2>All fields — present vs missing</h2>
<table><thead><tr><th>Field</th><th>Present</th><th>Missing</th><th>Present %</th><th>Missing %</th><th>Real %</th><th>Placeholder %</th></tr></thead>
<tbody>{field_rows}</tbody></table>
</body></html>
""",
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Shopify scrape CSV completeness.")
    parser.add_argument("csv_path", type=Path, help="Shopify-template scrape CSV")
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("shopify/out/shopify_scrape_metrics.json"),
        help="Write metrics JSON here",
    )
    parser.add_argument(
        "--canvas-out",
        type=Path,
        default=Path("canvases/shopify-scrape-metrics.canvas.tsx"),
        help="Write metrics canvas here",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = analyze(args.csv_path)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_canvas(report, args.canvas_out)
    # Mirror into Cursor project canvases path when relative default is used
    project_canvas = Path("/home/ubuntu/.cursor/projects/workspace/canvases/shopify-scrape-metrics.canvas.tsx")
    if args.canvas_out.resolve() != project_canvas.resolve():
        write_canvas(report, project_canvas)
    html_out = Path("shopify/out/shopify_scrape_metrics.html")
    write_html(report, html_out)
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    (downloads / html_out.name).write_bytes(html_out.read_bytes())
    print(json.dumps(report["summary"], indent=2))
    print(f"Wrote {args.json_out}")
    print(f"Wrote {args.canvas_out}")
    print(f"Wrote {html_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
