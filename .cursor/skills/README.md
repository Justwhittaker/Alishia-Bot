# Project skills

Slash-command skills for this workspace. Commit these so they travel with the repo.

| Skill | Command | Purpose |
|-------|---------|---------|
| `shopify_scrape` | `/shopify_scrape <url>` | Scrape a website into Shopify template CSV columns (**always unlisted**, **all variants**, **no VAT**) |
| `shopify_scrape_metric` | `/shopify_scrape_metric` | Canvas/table sanity check: products, **variants**, categories, present vs missing |
| `shopify_csv` | `/shopify_csv` | Convert an existing scraped CSV → Shopify import CSV (**always unlisted**, **no VAT**) |

## Lessons

Reusable learnings live in `.cursor/lessons/`. Read the relevant lesson before
changing scrape/import behavior.

| Lesson | Topic |
|--------|-------|
| `shopify-scrape-all-variants.md` | Always export every storefront variant; metrics must count variants |
