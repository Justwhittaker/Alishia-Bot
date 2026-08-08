---
name: shopify_scrape_metric
description: >-
  Builds a Shopify scrape sanity-check canvas/table showing products scraped,
  categories found, and present vs missing field coverage (with percentages)
  for a Shopify-template CSV. Use when the user invokes /shopify_scrape_metric
  or asks for scrape completeness / missing-data metrics on a Shopify CSV.
disable-model-invocation: true
---

# /shopify_scrape_metric — scrape completeness canvas

## Goal

When Justin runs **`/shopify_scrape_metric`**, analyze a Shopify-template scrape
CSV and refresh an interactive canvas that shows:

- number of **products** scraped
- number of **categories**
- **present vs missing** data per template field (counts + %)
- real vs placeholder coverage
- unlisted / Published=false counts

This is a **sanity check** after `/shopify_scrape` or `/shopify_csv`.

## Paths

| Role | Path |
|------|------|
| Skill | `.cursor/skills/shopify_scrape_metric/SKILL.md` |
| Analyzer | `.cursor/skills/shopify_scrape_metric/scripts/analyze_shopify_scrape.py` |
| Default CSV | `shopify/out/shopify_scrape_unlisted.csv` |
| Metrics JSON | `shopify/out/shopify_scrape_metrics.json` |
| Canvas (repo) | `canvases/shopify-scrape-metrics.canvas.tsx` |
| Canvas (IDE) | `/home/ubuntu/.cursor/projects/workspace/canvases/shopify-scrape-metrics.canvas.tsx` |

Template reference for field list:
`shopify/shopify_product_import_example.csv`

## Workflow

Copy and track:

```
Shopify scrape metric:
- [ ] 1. Locate Shopify-template CSV
- [ ] 2. Run analyze_shopify_scrape.py
- [ ] 3. Refresh canvas with embedded REPORT
- [ ] 4. MUST open canvas via open_resource
- [ ] 5. Brief chat summary tables
```

### 1. Locate CSV

Prefer, in order:

1. Path passed after `/shopify_scrape_metric`
2. Newest `shopify/out/*shopify*unlisted*.csv`
3. `shopify/shopify_product_import_example.csv` only if Justin asks to metric the template

### 2–3. Analyze + write canvas

```bash
python3 .cursor/skills/shopify_scrape_metric/scripts/analyze_shopify_scrape.py \
  "PATH/TO/shopify_csv.csv" \
  --json-out "shopify/out/shopify_scrape_metrics.json" \
  --canvas-out "canvases/shopify-scrape-metrics.canvas.tsx"
```

The script also mirrors the canvas to:
`/home/ubuntu/.cursor/projects/workspace/canvases/shopify-scrape-metrics.canvas.tsx`

### 4. MUST open the canvas (required)

After writing the canvas, **always** open it with cursor-app-control
`open_resource` before ending the turn.

1. `GetMcpTools` for server `cursor-app-control`, tool `open_resource` (if needed)
2. Call:

```
CallMcpTool server=cursor-app-control toolName=open_resource
arguments: {
  "uri": "file:///home/ubuntu/.cursor/projects/workspace/canvases/shopify-scrape-metrics.canvas.tsx"
}
```

Also link in chat:

[shopify scrape metrics](/home/ubuntu/.cursor/projects/workspace/canvases/shopify-scrape-metrics.canvas.tsx)

If `cursor-app-control` is unavailable in this environment, open/read the canvas
path another way if possible, and still include the markdown link. Do not skip
trying `open_resource` first.

### 5. Chat summary (brief)

Show only:

1. Summary: Products, Categories, Fields with missing, Unlisted count
2. Top missing fields table (field → missing %)
3. Category tally (category → products)

Do not dump every field row in chat — the canvas has the full table.

## Coverage rules

- Product-level fields (Title, Body, Vendor, …) are scored on **product rows**
  (rows with Title filled).
- Variant fields are scored on product + variant rows.
- Image fields are scored on all rows.
- Placeholder values (e.g. `0.00` price, “Product details coming soon”, CDN
  placeholder image) count as **present** but are also tracked under
  **placeholder %**.

## Related skills

- `/shopify_scrape` — scrape a website into the Shopify template CSV
- `/shopify_csv` — convert an existing scrape CSV into the Shopify template
