# Lesson: Always export all Shopify variants

**Date:** 2026-08-11  
**Source:** Mullingar Pewter scrape (`/shopify_scrape https://mullingarpewter.com/`)  
**Applies to:** `/shopify_scrape`, `/shopify_scrape_metric`, `/shopify_csv`

## What went wrong

The first Mullingar Pewter CSV looked import-ready (147 products, prices correct,
unlisted, no VAT) but **72 of 147 products had multiple storefront variants**
(sizes, designs, sets). The scraper only wrote `variants[0]` — so goblets,
tankards, and measure sets would have imported incomplete.

## Rule going forward

1. **`/shopify_scrape` must export every variant**, never first-variant-only.
   - Prefer Shopify `product.json` / `products.json` `variants[]` + `options[]`.
   - CSV shape: first row = product fields + variant 1; following rows = same
     Handle + Option*/Variant* only; then image-only rows.
2. **`/shopify_scrape_metric` must report variants**, not just products:
   - `variants` (priced rows), `multiVariantProducts`, avg/max variants,
     top multi-variant handles.
3. Keep existing hard rules: `Status=unlisted`, `Published=false`,
   `Variant Taxable=false` (no VAT) unless Justin overrides.

## Quick verification

After a scrape, confirm:

```text
variants_written ≈ sum of storefront variant counts
multi_variant_products > 0 when the catalog has options
```

Spot-check one known multi-SKU product (e.g. Kells goblets) has N priced rows.

## Related files

- `.cursor/skills/shopify_scrape/scripts/scrape_shopify_catalog.py`
- `.cursor/skills/shopify_scrape_metric/scripts/analyze_shopify_scrape.py`
- `.cursor/lessons/shopify-scrape-all-variants.md` (this file)
