#!/usr/bin/env bash
# Run /shopify_scrape in Docker (no custom image build — mounts the scraper script).
# Usage:
#   ./shopify/docker/run-scrape.sh "https://irishfamilysurnames.com/" "Irish Family Surnames" 500
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
URL="${1:-https://irishfamilysurnames.com/}"
VENDOR="${2:-Irish Family Surnames}"
LIMIT="${3:-500}"
SITEMAP="${4:-$ROOT/scraped-irish-family-surnames/product-sitemap.xml}"
OUT="${5:-$ROOT/shopify/out/shopify_scrape_unlisted.csv}"

mkdir -p "$ROOT/shopify/out"

docker run --rm \
  -v "$ROOT/.cursor/skills/shopify_scrape/scripts:/app/scripts:ro" \
  -v "$ROOT/shopify/out:/data/out" \
  -v "$ROOT/scraped-irish-family-surnames:/data/sitemaps:ro" \
  python:3.12-slim \
  python3 /app/scripts/scrape_shopify_catalog.py \
  "$URL" \
  -o "/data/out/$(basename "$OUT")" \
  --vendor "$VENDOR" \
  --limit "$LIMIT" \
  --delay 0.15 \
  --local-sitemap "$SITEMAP"

echo "Output: $OUT"
