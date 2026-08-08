# Shopify product CSV tools

## `/shopify_csv` skill

Convert scraped website CSVs into Shopify Admin import CSVs.

- Skill: `.cursor/skills/shopify_csv/SKILL.md`
- Script: `.cursor/skills/shopify_csv/scripts/convert_to_shopify_csv.py`

**Always outputs `Status=unlisted` and `Published=false`.**

```bash
python3 .cursor/skills/shopify_csv/scripts/convert_to_shopify_csv.py \
  path/to/scraped.csv \
  -o shopify/out/scraped_shopify_unlisted.csv
```

Converted examples from this repo live in `shopify/out/`.

## Example templates

| File | Use |
|------|-----|
| `shopify_product_import_example.csv` | Full standard header set |
| `shopify_product_import_example_minimal.csv` | Common shorter header set |

Sample products in the templates: ceramic mug (+ images), cotton tee (S/M/L), digital guide.

## Import

Shopify Admin → **Products** → **Import** → upload the CSV.

Official docs: https://help.shopify.com/en/manual/products/import-export/using-csv
