---
name: shopify-csv
description: >-
  Converts a source product CSV into a Shopify Admin import CSV that matches
  shopify/shopify_product_import_example.csv, repairs poor/missing fields so
  imports do not fail, always forces Status=unlisted and Published=false, and
  applies optional **...** custom edits (e.g. add collections to all items).
  Use when the user invokes /shopify_csv, /shopify-csv, passes a csv file path
  for Shopify import cleanup, or asks to convert scraped/poor CSV data into
  importable Shopify products.
disable-model-invocation: true
---

# /shopify_csv — CSV path → Shopify import (template-perfect + custom edits)

## Goal

When Justin runs **`/shopify_csv <csv file path>`**, take that CSV (often messy
or scraped), reshape it to match the gold-standard Shopify product import
template, fill safe placeholders so Admin import will not fail, keep every
product **unlisted**, then apply any **`**...**` custom edits** from the same
message.

Canonical slash forms: **`/shopify_csv`** and **`/shopify-csv`**.

### Hard requirements (never skip)

1. **Require a CSV path**
   - Look for `<csv file path>` immediately after `/shopify_csv` (absolute or
     workspace-relative).
   - Also accept a bare path on the next line if the slash command has no arg.
   - If no path is present, ask once for the path — do not guess a random CSV.
2. **Perfect against the example template**
   - Column order and names must match
     `/workspace/shopify/shopify_product_import_example.csv`
     (repo-relative: `shopify/shopify_product_import_example.csv`).
   - Convert poor headers/values into that schema; never invent alternate header
     spellings that Shopify will ignore.
3. **Import must not fail**
   - Validate / repair images; replace bad URLs with the Shopify CDN placeholder.
   - Fill Title, Handle, Option1, Variant Price, inventory/fulfillment defaults,
     Body, Status, Published, etc. when missing or invalid.
4. **ALWAYS unlisted**
   - `Status=unlisted` and `Published=false` on every row (including image-only
     rows). Never blank Status (Shopify treats blank as `active`).
5. **Apply `**...**` custom edits** when present in the user message (see below).

## Invocation shape

```text
/shopify_csv <csv file path>

**optional custom edits directive
value line 1
value line 2 **
```

Example:

```text
/shopify_csv /workspace/scraped-irish-family-surnames/all_surnames_sitemap.csv

**add collections to all items
Heraldic Irish Family Names
Gifts under €25 **
```

### Custom edits block (`**` … `**`)

Scan the **same user message** (text after the CSV path) for a block that
starts with `**` and ends with `**`.

Rules:

- Opening `**` begins the block; closing `**` ends it (may sit on the last line).
- First non-empty line inside the block is the **directive**.
- Remaining non-empty lines are **values** for that directive.
- Multiple `**...**` blocks are allowed; apply them in order.
- If there is no `**...**` block, skip custom edits (conversion still runs).

Supported directives (case-insensitive):

| Directive | Values | Effect |
|-----------|--------|--------|
| `add collections to all items` | One collection name per line | Append each collection name to **Tags** on every product row (comma-separated, de-duped) so Shopify automated collections / filtering can pick them up without changing the template headers. |
| `add tags to all items` | One tag per line | Append each tag to **Tags** on every product row. |
| `set vendor` | Single vendor line | Overwrite **Vendor** on every product row. |
| `set type` | Single type line | Overwrite **Type** on every product row. |

Unknown directives → warn in the summary; do not abort the conversion.

## Paths

| Role | Path |
|------|------|
| Skill | `.cursor/skills/shopify-csv/SKILL.md` |
| Converter | `.cursor/skills/shopify-csv/scripts/convert_to_shopify_csv.py` |
| **Gold-standard template** | `/workspace/shopify/shopify_product_import_example.csv` |
| Minimal reference | `shopify/shopify_product_import_example_minimal.csv` |
| Default output dir | `shopify/out/` (create if needed) |

Also copy finished CSVs to `~/Downloads/` when that helps Justin grab the file.

## Workflow

Copy and track:

```
Shopify CSV:
- [ ] 1. Resolve <csv file path> from the /shopify_csv invocation
- [ ] 2. Parse any **...** custom-edit blocks from the same message
- [ ] 3. Run converter with --template shopify_product_import_example.csv
- [ ] 4. Verify headers match template; Status=unlisted; Published=false
- [ ] 5. Confirm custom edits applied (collections/tags/etc.)
- [ ] 6. Save to shopify/out/ + Downloads; brief summary for Justin
```

### 1. Resolve the CSV path

Prefer, in order:

1. Path argument after `/shopify_csv` / `/shopify-csv`
2. First filesystem path token on the following line that ends in `.csv`
3. Only if still missing: ask Justin for the path

Resolve relative paths against the workspace root (`/workspace` here).

### 2. Parse custom edits

Extract every `**...**` block from the user message. Pass them to the converter
via `--edits` (inline text) or a temp `--edits-file`.

### 3. Run the converter

From the repo root:

```bash
python3 .cursor/skills/shopify-csv/scripts/convert_to_shopify_csv.py \
  "PATH/TO/source.csv" \
  -o "shopify/out/$(basename PATH/TO/source.csv .csv)_shopify_unlisted.csv" \
  --template "/workspace/shopify/shopify_product_import_example.csv" \
  --edits $'**add collections to all items\nHeraldic Irish Family Names\nGifts under €25 **' \
  --vendor "Imported Catalog"
```

Flags:

| Flag | Meaning |
|------|---------|
| `input_csv` (positional) | **Required** source CSV path |
| `-o/--output` | Output path (default: `shopify/out/<stem>_shopify_unlisted.csv`) |
| `--template` | Gold-standard header file (default: `shopify/shopify_product_import_example.csv`) |
| `--edits` | Raw `**...**` custom-edit text from the user message |
| `--edits-file` | File containing the same custom-edit text |
| `--vendor` | Default Vendor when source has none |
| `--skip-image-validation` | Faster; only if Justin asks |

Default behavior **validates images**. Keep that on unless Justin opts out.

Then copy to Downloads:

```bash
mkdir -p "$HOME/Downloads"
cp -f "shopify/out/..._shopify_unlisted.csv" "$HOME/Downloads/"
```

### 4. Verify template + unlisted

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
    if (row.get("Status") or "").strip().lower() != "unlisted":
        bad.append((i, "Status", row.get("Status")))
    if (row.get("Published") or "").strip().lower() != "false":
        bad.append((i, "Published", row.get("Published")))
if bad:
    raise SystemExit(f"UNLISTED CHECK FAILED: {bad[:10]}")
print(f"OK: headers match template; {len(rows)} data rows unlisted")
PY
shopify/out/SOURCE_shopify_unlisted.csv \
/workspace/shopify/shopify_product_import_example.csv
```

### 5. Summarize

Tell Justin:

- Input path + output path(s)
- Product count / rows
- Images kept vs replaced
- Custom edits applied (directive + values)
- Confirmation: headers match example template; **all products unlisted**
- Reminder: Shopify Admin → **Products → Import**

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

1. Must be `http` / `https`
2. Validate with HEAD (fallback GET + byte sniff)
3. Reject `text/html`, JSON, empty, or non-image payloads
4. Accept jpeg/png/gif/webp signatures or `image/*` content-type
5. If all candidates fail → placeholder image

Never write a scraped HTML page URL into `Image Src`.

## Fallback if a store rejects `Status=unlisted`

1. Tell Justin — do not auto-change.
2. Only if he confirms: regenerate with `Status=draft` and keep `Published=false`.
3. Never silently switch to `active`.

## Do not

- Run without a CSV path when one was expected
- Ignore `**...**` custom edits in the same message
- Emit headers that differ from `shopify_product_import_example.csv`
- Publish products (`Published=true` / `Status=active`)
- Pass through corrupt image URLs
- Drop required Shopify variant scaffolding (Option1 + Price)
