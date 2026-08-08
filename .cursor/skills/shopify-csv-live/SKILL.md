---
name: shopify-csv-live
description: >-
  Live Shopify product CSV import builder. Uses /shopify_csv as the source of
  truth for template headers, field repair, image validation, and **...**
  custom edits, but always forces Status=active and Published=true so products
  go live on import. Use when the user invokes /shopify_csv_live,
  /shopify-csv-live, asks for a live/push/publish Shopify CSV, or wants the
  same conversion as /shopify_csv but with active published products.
disable-model-invocation: true
---

# /shopify_csv_live — CSV path → live Shopify import (active + published)

## Goal

When Justin runs **`/shopify_csv_live <csv file path>`**, run the same pipeline
as **`/shopify_csv`** (source of truth), then force every row to:

- **`Status=active`**
- **`Published=true`**

Still apply any **`**...**` custom edits** from the same message.

Canonical slash forms: **`/shopify_csv_live`** and **`/shopify-csv-live`**.

### Source of truth

**Do not fork conversion rules.** Read and follow:

`.cursor/skills/shopify-csv/SKILL.md` (`/shopify_csv`)

That skill owns:

- CSV path resolution
- Gold-standard headers from `/workspace/shopify/shopify_product_import_example.csv`
- Poor-data repair / placeholders / image validation
- `**...**` custom-edit parsing and directives

This skill only changes the publish mode to **live**.

### Hard requirements (never skip)

1. Require `<csv file path>` (same rules as `/shopify_csv`).
2. Use the shared converter with **`--live`**.
3. **ALWAYS live**
   - `Status=active` on every row (including image-only rows)
   - `Published=true` on every row
   - Never leave Status/Published blank
4. Apply `**...**` custom edits when present (same directives as `/shopify_csv`).
5. Warn Justin clearly that this CSV will **publish products to the Online Store**.

## Invocation shape

```text
/shopify_csv_live <csv file path>

**optional custom edits directive
value line 1
value line 2 **
```

Example:

```text
/shopify_csv_live /workspace/scraped-irish-family-surnames/all_surnames_sitemap.csv

**add collections to all items
Heraldic Irish Family Names
Gifts under €25 **
```

## Paths

| Role | Path |
|------|------|
| This skill | `.cursor/skills/shopify-csv-live/SKILL.md` |
| Source-of-truth skill | `.cursor/skills/shopify-csv/SKILL.md` |
| Shared converter | `.cursor/skills/shopify-csv/scripts/convert_to_shopify_csv.py` |
| Gold-standard template | `/workspace/shopify/shopify_product_import_example.csv` |
| Default output dir | `shopify/out/` |

## Workflow

Copy and track:

```
Shopify CSV Live:
- [ ] 1. Resolve <csv file path> (same as /shopify_csv)
- [ ] 2. Parse any **...** custom-edit blocks from the same message
- [ ] 3. Run shared converter with --live
- [ ] 4. Verify headers match template; Status=active; Published=true
- [ ] 5. Confirm custom edits applied
- [ ] 6. Save to shopify/out/ + Downloads; warn Justin this is LIVE
```

### Run the converter (live mode)

```bash
python3 .cursor/skills/shopify-csv/scripts/convert_to_shopify_csv.py \
  "PATH/TO/source.csv" \
  --live \
  -o "shopify/out/$(basename PATH/TO/source.csv .csv)_shopify_live.csv" \
  --template "/workspace/shopify/shopify_product_import_example.csv" \
  --edits $'**add collections to all items\nHeraldic Irish Family Names\nGifts under €25 **' \
  --vendor "Imported Catalog"
```

`--live` is the only intentional difference from `/shopify_csv`.

Default output name when `-o` is omitted: `shopify/out/<stem>_shopify_live.csv`.

Then copy to Downloads:

```bash
mkdir -p "$HOME/Downloads"
cp -f "shopify/out/..._shopify_live.csv" "$HOME/Downloads/"
```

### Verify template + live

```bash
python3 - <<'PY'
import csv, sys
from pathlib import Path
out, template = Path(sys.argv[1]), Path(sys.argv[2])
with template.open(newline="", encoding="utf-8-sig") as f:
    want = next(csv.reader(f))
with out.open(newline="", encoding="utf-8-sig") as f:
    got = next(csv.reader(f))
    rows = list(csv.DictReader(f))
if got != want:
    raise SystemExit(f"HEADER MISMATCH:\n want={want}\n got={got}")
bad = []
for i, row in enumerate(rows, start=2):
    if (row.get("Status") or "").strip().lower() != "active":
        bad.append((i, "Status", row.get("Status")))
    if (row.get("Published") or "").strip().lower() != "true":
        bad.append((i, "Published", row.get("Published")))
if bad:
    raise SystemExit(f"LIVE CHECK FAILED: {bad[:10]}")
print(f"OK: headers match template; {len(rows)} data rows LIVE (active + published)")
PY
shopify/out/SOURCE_shopify_live.csv \
/workspace/shopify/shopify_product_import_example.csv
```

### Summarize

Tell Justin:

- Input path + output path(s)
- Product count / rows
- Images kept vs replaced
- Custom edits applied (if any)
- Confirmation: headers match example template; **all products LIVE**
  (`Status=active`, `Published=true`)
- Explicit warning: importing this file will make products visible/sellable
- Reminder: Shopify Admin → **Products → Import**

## Difference vs `/shopify_csv`

| | `/shopify_csv` | `/shopify_csv_live` |
|--|----------------|---------------------|
| Status | `unlisted` | `active` |
| Published | `false` | `true` |
| Default output | `*_shopify_unlisted.csv` | `*_shopify_live.csv` |
| Template / repairs / `**edits**` | shared | shared |

## Do not

- Reimplement conversion logic separately from `/shopify_csv`
- Emit unlisted/draft rows from this skill
- Skip `**...**` custom edits when present
- Soften the live warning in the summary
