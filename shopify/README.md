# Shopify product CSV tools

Column template source of truth: `shopify_product_import_example.csv`.

## Skills

| Command | Purpose |
|---------|---------|
| `/shopify_scrape <url>` | Scrape a website → Shopify template CSV (**always unlisted**) |
| `/shopify_scrape_metric` | Canvas/table: products, categories, present vs missing |
| `/shopify_csv` | Convert an existing scrape CSV → Shopify template (**always unlisted**) |

```bash
# Scrape a site into the template columns
python3 .cursor/skills/shopify_scrape/scripts/scrape_shopify_catalog.py \
  "https://example.com/shop" \
  -o shopify/out/shopify_scrape_unlisted.csv

# Sanity-check metrics + canvas
python3 .cursor/skills/shopify_scrape_metric/scripts/analyze_shopify_scrape.py \
  shopify/out/shopify_scrape_unlisted.csv

# Convert a non-Shopify scrape CSV
python3 .cursor/skills/shopify_csv/scripts/convert_to_shopify_csv.py \
  path/to/scraped.csv \
  -o shopify/out/scraped_shopify_unlisted.csv
```

Outputs land in `shopify/out/`. Metrics canvas: `canvases/shopify-scrape-metrics.canvas.tsx`.

## Example templates

| File | Use |
|------|-----|
| `shopify_product_import_example.csv` | Full standard header set (51 cols) |
| `shopify_product_import_example_minimal.csv` | Common shorter header set |

## Import

Shopify Admin → **Products** → **Import** → upload the CSV.

## Docker scrape (recommended)

Run the scraper in an isolated Python container — no host Python setup required.

```bash
./shopify/docker/run-scrape.sh "https://irishfamilysurnames.com/" "Irish Family Surnames" 500
```

Output lands in `shopify/out/shopify_scrape_unlisted.csv`. Uses `python:3.12-slim` with the scraper script mounted in.

Optional custom image build (if your Docker supports overlay):

```bash
docker compose -f shopify/docker/docker-compose.yml build   # uses shopify/docker/Dockerfile
```

Official docs: https://help.shopify.com/en/manual/products/import-export/using-csv
