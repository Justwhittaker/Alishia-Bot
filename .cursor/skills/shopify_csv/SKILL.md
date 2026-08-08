---
name: shopify_csv
description: >-
  Converts scraped product CSV data from another website into a digestible
  Shopify Admin product-import CSV. Always forces products to Status=unlisted
  and Published=false, maps as many source fields as possible, validates image
  URLs (replaces corrupted/non-image links), and fills Shopify-safe placeholders
  so imports do not fail. Use when the user invokes /shopify_csv, asks to
  convert a scrape CSV for Shopify, or needs an unlisted Shopify product import
  file from scraped catalog data.
disable-model-invocation: true
---

# /shopify_csv — scraped CSV → Shopify import CSV (always unlisted)

## Goal

When Justin runs **`/shopify_csv`**, convert a **scraped** product CSV into a
**Shopify Admin → Products → Import** friendly CSV that is safe to upload.

### Hard requirements (never skip)

1. **ALWAYS unlisted**
   - Set **`Status` = `unlisted`** on every product row (and image-only rows).
   - Set **`Published` = `false`** on every product row (and image-only rows).
   - Do **not** leave Status blank (Shopify defaults blank Status to `active`).
   - Do **not** set Published to `true`.
2. **Pull as much data as possible** from the scraped CSV (title, handle/slug,
   description, vendor, type/category, tags, SKU, price, compare-at, barcode,
   weight, qty, options, images, SEO, source URL).
3. **Images must not be corrupted**
   - Validate image URLs (HTTP, content-type / magic bytes).
   - Drop HTML error pages, JSON, empty, or non-image payloads.
   - Replace bad/missing images with a Shopify CDN placeholder so import still works.
4. **Missing fields → Shopify-safe placeholders** so the import does not fail
   (Title, Handle, Option1, Variant Price, fulfillment/inventory defaults, body, etc.).

## Paths

| Role | Path |
|------|------|
| Skill | `.cursor/skills/shopify_csv/SKILL.md` |
| Converter | `.cursor/skills/shopify_csv/scripts/convert_to_shopify_csv.py` |
| Example Shopify template | `shopify/shopify_product_import_example.csv` |
| Default output dir | `shopify/out/` (create if needed) |

Also copy finished CSVs to `~/Downloads/` when running in an environment where
that helps Justin grab the file.

## Workflow

Copy and track:

```
Shopify CSV:
- [ ] 1. Locate input scraped CSV (arg, open file, or newest scrape CSV)
- [ ] 2. Run convert_to_shopify_csv.py (validate images ON by default)
- [ ] 3. Verify every Status=unlisted and Published=false
- [ ] 4. Spot-check titles, prices, image URLs / placeholders
- [ ] 5. Save to shopify/out/ + Downloads; brief summary for Justin
```

### 1. Locate the scraped CSV

Prefer, in order:

1. Path the user passed after `/shopify_csv` (file path or glob)
2. Currently focused / recently discussed CSV in the workspace
3. Newest `*.csv` under `scraped-*/`, `data/`, `shopify/`, or Downloads that is
   **not** already a `*_shopify_unlisted.csv`

If none found, ask for the scraped CSV path (only in that case).

### 2. Run the converter

From the repo root:

```bash
python3 .cursor/skills/shopify_csv/scripts/convert_to_shopify_csv.py \
  "PATH/TO/scraped.csv" \
  -o "shopify/out/scraped_shopify_unlisted.csv" \
  --vendor "Imported Catalog"
```

Flags:

| Flag | Meaning |
|------|---------|
| `-o/--output` | Output path (default: `<input>_shopify_unlisted.csv`) |
| `--vendor` | Default Vendor when source has none |
| `--skip-image-validation` | Faster; only use if Justin asks (still fills empty images) |

Default behavior **validates images**. Keep that on unless Justin opts out.

Then copy to Downloads:

```bash
mkdir -p "$HOME/Downloads"
cp -f "shopify/out/scraped_shopify_unlisted.csv" "$HOME/Downloads/"
```

### 3. Verify unlisted (required)

```bash
python3 - <<'PY'
import csv, sys
path = sys.argv[1]
bad = []
with open(path, newline="", encoding="utf-8") as f:
    for i, row in enumerate(csv.DictReader(f), start=2):
        if (row.get("Status") or "").strip().lower() != "unlisted":
            bad.append((i, "Status", row.get("Status")))
        if (row.get("Published") or "").strip().lower() != "false":
            bad.append((i, "Published", row.get("Published")))
if bad:
    raise SystemExit(f"UNLISTED CHECK FAILED: {bad[:10]}")
print("OK: all rows Status=unlisted and Published=false")
PY
shopify/out/scraped_shopify_unlisted.csv
```

If this fails, fix and regenerate — **do not** hand Justin a CSV that can publish live.

### 4. Spot-check

- First product row has Title + Handle + Variant Price
- Option1 Name/Value present (`Title` / `Default Title` when no variants)
- Image Src is either a validated image URL or the Shopify placeholder
- Report placeholder counts from the script stdout to Justin

### 5. Summarize

Tell Justin:

- Output path(s)
- Product count / rows
- Images kept vs replaced
- Confirmation: **all products unlisted** (`Status=unlisted`, `Published=false`)
- Reminder: Shopify Admin → **Products → Import**

## Column mapping (scraped → Shopify)

The script auto-maps common scrape headers (case/spacing insensitive), including:

| Logical | Example scraped headers |
|---------|-------------------------|
| Title | `title`, `name`, `product_name`, `surname`, `business_name` |
| Handle | `handle`, `slug`, `url_handle` |
| Body | `description`, `body_html`, `about_blurb`, `details` |
| Vendor | `vendor`, `brand`, `supplier` |
| Type | `type`, `category`, `venue_category` |
| SKU | `sku`, `product_id`, `id` |
| Price | `price`, `sale_price`, `amount` |
| Image | `image`, `image_url`, `image_src`, `thumbnail`, `photo` |
| URL | `url`, `product_url`, `source_url` |
| Options | `size` / `color` → Option1 when present |

Unmapped extra image-like columns are still considered for Image Src.

## Placeholders used when data is missing

| Field | Placeholder |
|-------|-------------|
| Title | `Imported Product {n}` (or derived from slug/URL) |
| Handle | slugified title / `imported-product-{n}` |
| Body (HTML) | `<p>Product details coming soon.</p>` |
| Vendor | `Imported Catalog` (or `--vendor`) |
| Type | `General` |
| Option1 | `Title` / `Default Title` |
| Variant SKU | `IMP-{HANDLE}` |
| Variant Price | `0.00` |
| Variant Grams / Qty | `0` |
| Inventory Tracker | `shopify` |
| Inventory Policy | `deny` |
| Fulfillment Service | `manual` |
| Requires Shipping / Taxable | `true` |
| Image Src | Shopify CDN placeholder image |
| SEO Description | `Imported product — review before publishing.` |
| **Status** | **`unlisted` (always)** |
| **Published** | **`false` (always)** |

## Image integrity rules

For each candidate image URL:

1. Must be `http` / `https`
2. Validate with HEAD (fallback GET + byte sniff)
3. Reject `text/html`, JSON bodies, tiny/empty payloads, bad HTTP status
4. Accept jpeg/png/gif/webp signatures or `image/*` content-type
5. If all candidates fail → **placeholder image** (import still succeeds)

Never write a scraped HTML page URL into `Image Src`.

## Fallback if a store rejects `Status=unlisted`

`unlisted` is a Shopify product status (Admin API 2025-10+). If an older shop’s
CSV import rejects it:

1. Re-run is **not** automatic — tell Justin.
2. Only if Justin confirms, regenerate with `Status=draft` **and** keep
   `Published=false` (still not live on the Online Store).
3. Never silently switch to `active`.

## Reference templates

- Full example: `shopify/shopify_product_import_example.csv`
- Minimal example: `shopify/shopify_product_import_example_minimal.csv`
- Docs: https://help.shopify.com/en/manual/products/import-export/using-csv

## Do not

- Publish products (`Published=true` / `Status=active`) from this skill
- Pass through corrupt image URLs
- Drop required Shopify variant scaffolding (Option1 + Price)
- Ask Justin to manually fix Status/Published after a successful conversion
