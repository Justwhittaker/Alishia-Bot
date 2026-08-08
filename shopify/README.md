# Shopify product CSV tools

Column template source of truth: `shopify_product_import_example.csv`
(absolute path on cloud agents: `/workspace/shopify/shopify_product_import_example.csv`).

## Skills

| Command | Purpose |
|---------|---------|
| `/shopify_csv <csv file path>` | Convert/repair any CSV → Shopify template (**always unlisted**), optional `**custom edits**` |
| `/shopify_csv_live <csv file path>` | Same pipeline as `/shopify_csv`, but **`Status=active` + `Published=true`** |

```bash
# Safe (unlisted) — /shopify_csv
python3 .cursor/skills/shopify-csv/scripts/convert_to_shopify_csv.py \
  "path/to/source.csv" \
  -o shopify/out/source_shopify_unlisted.csv \
  --template shopify/shopify_product_import_example.csv \
  --edits $'**add collections to all items\nHeraldic Irish Family Names\nGifts under €25 **'

# Live (active + published) — /shopify_csv_live
python3 .cursor/skills/shopify-csv/scripts/convert_to_shopify_csv.py \
  "path/to/source.csv" \
  --live \
  -o shopify/out/source_shopify_live.csv \
  --template shopify/shopify_product_import_example.csv \
  --edits $'**add collections to all items\nHeraldic Irish Family Names\nGifts under €25 **'
```

Outputs land in `shopify/out/`.

### Custom edits (`**` … `**`)

After the CSV path in chat, wrap directives in `**`:

```text
/shopify_csv /workspace/path/to/file.csv

**add collections to all items
Heraldic Irish Family Names
Gifts under €25 **
```

## Example templates

| File | Use |
|------|-----|
| `shopify_product_import_example.csv` | Full standard header set (51 cols) — gold standard |
| `shopify_product_import_example_minimal.csv` | Common shorter header set |

## Import

Shopify Admin → **Products** → **Import** → upload the CSV.

Official docs: https://help.shopify.com/en/manual/products/import-export/using-csv
