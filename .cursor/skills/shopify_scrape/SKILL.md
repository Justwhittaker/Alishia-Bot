---
name: shopify_scrape
description: >-
  Scrapes product data from a website URL supplied after the /shopify_scrape
  prompt and writes a Shopify Admin product-import CSV using the exact column
  template in shopify/shopify_product_import_example.csv. Always forces
  Status=unlisted and Published=false, validates images, and fills safe
  placeholders for missing fields. Use when the user invokes /shopify_scrape or
  asks to scrape a store/catalog site into Shopify CSV columns.
disable-model-invocation: true
---

# /shopify_scrape — website → Shopify template CSV

## Goal

When Justin runs:

```text
/shopify_scrape https://example.com/shop
```

scrape that site’s product catalog and build a CSV whose **headers match**
`shopify/shopify_product_import_example.csv` exactly.

### Hard requirements

1. **Template columns** — output must use the full header row from
   `shopify/shopify_product_import_example.csv` (same names/order).
2. **ALWAYS unlisted**
   - `Status=unlisted`
   - `Published=false`
   - Never `active` / `Published=true`.
3. Pull as much product data as the site exposes (title, body, vendor, type,
   category, tags, options, SKU, price, compare-at, barcode, weight, images,
   SEO, Google Shopping fields when present).
4. Validate images; replace corrupt/non-image URLs with the Shopify CDN
   placeholder.
5. Fill Shopify-safe placeholders for missing required variant fields so import
   does not fail.
6. After a successful scrape, optionally remind Justin to run
   **`/shopify_scrape_metric`** for the sanity-check canvas.

## Paths

| Role | Path |
|------|------|
| Skill | `.cursor/skills/shopify_scrape/SKILL.md` |
| Scraper | `.cursor/skills/shopify_scrape/scripts/scrape_shopify_catalog.py` |
| Column template | `shopify/shopify_product_import_example.csv` |
| Default output | `shopify/out/shopify_scrape_unlisted.csv` |
| Run metadata | `shopify/out/shopify_scrape_unlisted.meta.json` |

## Workflow

Copy and track:

```
Shopify scrape:
- [ ] 1. Read URL after /shopify_scrape (required)
- [ ] 2. Run scrape_shopify_catalog.py against that URL
- [ ] 3. Verify Status=unlisted + Published=false on all rows
- [ ] 4. Copy CSV to ~/Downloads
- [ ] 5. Brief summary (products, rows, images kept/replaced)
```

### 1. URL argument (required)

The website must appear **after** the slash command, e.g.:

- `/shopify_scrape https://irishfamilysurnames.com/shop/`
- `/shopify_scrape https://example.myshopify.com/collections/all`

If no URL is provided, ask for one and stop.

### 2. Run scraper

```bash
python3 .cursor/skills/shopify_scrape/scripts/scrape_shopify_catalog.py \
  "https://SITE" \
  -o "shopify/out/shopify_scrape_unlisted.csv" \
  --vendor "Imported Catalog" \
  --limit 200
```

Useful flags:

| Flag | Default | Meaning |
|------|---------|---------|
| `--limit` | `200` | Max products |
| `--vendor` | `Imported Catalog` | Fallback Vendor |
| `--delay` | `0.35` | Seconds between product fetches |
| `--skip-image-validation` | off | Only if Justin asks |

Discovery order inside the script:

1. Product sitemaps (`sitemap.xml`, `product-sitemap.xml`, Shopify product sitemaps)
2. HTML listing pages (`/shop/`, `/collections/all`)
3. Shopify `products.json` when available
4. Per-product page parse via JSON-LD + meta + Shopify `.json` enrichment

### 3. Verify unlisted

```bash
python3 - <<'PY'
import csv,sys
path=sys.argv[1]
bad=[]
with open(path,newline='',encoding='utf-8') as f:
    for i,r in enumerate(csv.DictReader(f), start=2):
        if (r.get('Status') or '').strip().lower()!='unlisted': bad.append((i,'Status',r.get('Status')))
        if (r.get('Published') or '').strip().lower()!='false': bad.append((i,'Published',r.get('Published')))
if bad: raise SystemExit(bad[:10])
print('OK unlisted')
PY
shopify/out/shopify_scrape_unlisted.csv
```

### 4. Save for Justin

```bash
mkdir -p "$HOME/Downloads"
cp -f shopify/out/shopify_scrape_unlisted.csv "$HOME/Downloads/"
```

### 5. Summary

Report:

- Seed URL
- Product URLs found / products scraped / CSV rows
- Images kept vs placeholder replacements
- Output path
- Confirmation: **all products unlisted**

Then suggest: run `/shopify_scrape_metric` on the output CSV.

## Related skills

- `/shopify_csv` — convert an already-scraped non-Shopify CSV into this template
- `/shopify_scrape_metric` — present/missing sanity-check canvas for a scrape CSV

## Do not

- Publish products
- Invent product prices/descriptions beyond declared placeholders
- Skip image validation unless Justin opts out
- Scrape behind logins / ignore robots intent on tiny polite delays
