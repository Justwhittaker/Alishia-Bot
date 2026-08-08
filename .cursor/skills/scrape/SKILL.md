---
name: scrape
description: >-
  Starts the MealDeals hospitality scrape rule and runs a fresh worldwide
  scrape refresh that upserts deals and marketing business contacts, corrects
  deal/logo image scraping, then updates the MealDeals website and metrics
  canvas with the newest data. Use when the user invokes /scrape, asks to
  refresh scrapes, or wants a new scrape pass.
disable-model-invocation: true
---

# /scrape — fresh hospitality scrape

## Goal

Start the hospitality scraping rule and run a **fresh scrape** across **all**
`TARGET_MARKETS` (currently 91 countries / 383 cities). Persist deals and a
separate marketing contact ledger, **update the MealDeals website so it serves
the newest scraped data**, refresh the metrics canvas, then **show the full
results breakdown** to the user.

**Project root:** `/Users/justinw/Projects/PRO4-Mealdeals` (symlink to JustinBot/MealDeals).

Prefer the project skill when present:
`/Users/justinw/Projects/PRO4-Mealdeals/.cursor/skills/scrape/SKILL.md`
(includes category taxonomy notes).

## Before scraping

1. Read and follow `/Users/justinw/Projects/PRO4-Mealdeals/.cursor/rules/hospitality-deal-scraping.mdc`.
2. Confirm Docker API is up (`mealdeals-api` on `:8000`) or start backend via `docker compose` in `/Users/justinw/Projects/PRO4-Mealdeals/backend`.
3. Apply migrations:

```bash
docker exec mealdeals-api alembic upgrade head
```

## Markets in scope

Always scrape the full `TARGET_MARKETS` list from
`/Users/justinw/Projects/PRO4-Mealdeals/backend/app/scrapers/markets.py`
(do **not** pass `only_new=true`). That list includes the seed markets
(GB, US, CA, AU, IE, NZ, PH, TH, NL, BS, JM) plus every expanded market
(Caribbean, Africa, Europe, MENA, Asia, LatAm, Pacific, etc.).

## Start the fresh scrape

Prefer a **synchronous** run so the response includes the full report:

```bash
curl -sS --max-time 1200 -X POST 'http://localhost:8000/api/v1/scrapers/scrape?wait=true'
```

If you must queue async:

```bash
curl -sS -X POST 'http://localhost:8000/api/v1/scrapers/scrape?wait=false'
docker restart mealdeals-celery   # if worker was restarted recently
# poll until complete, then:
curl -sS 'http://localhost:8000/api/v1/scrapers/report'
```

## What the scrape must capture

| Field | Required | Destination |
|-------|----------|-------------|
| Business name | yes | `marketing_contacts.business_name` + deal merchant |
| Website | yes (fallback source URL) | `marketing_contacts.website` |
| Telephone | when found | `marketing_contacts.phone` |
| Email | when found | `marketing_contacts.email` |
| About blurb | when About / description available | `marketing_contacts.about_blurb` |
| Venue category | yes (auto-tagged via parent taxonomy) | `marketing_contacts.venue_category` |
| Deal image (`img` / `png` / jpg / webp) | yes (see image scrape rules) | `deals.image_url` / scraped `image_url` |
| Company logo | yes when found | merchant / scraped `logo_url` (persist + expose to frontend) |

Also capture deal inventory per the hospitality rule.

## Image scrape — REQUIRED (FORCE photo order)

**FORCE RULE:** (1) deal/offer page → (2) merchant landing/menu → (3) dish-category
generic placeholder. Never skip ahead to generics when a site photo exists.
Never use the company logo as the deal hero.

Step 3 uses `backend/app/scrapers/deal_placeholders.py` (burgers, pasta, wine
vineyard, tagine, …). Unknown dishes are learned via Wikimedia and saved in
`backend/app/scrapers/data/dish_placeholders.json`. See the project skill for
full detail.

### 1. Deal photo from the offer page (primary)

- Pull the deal image **exactly from the deal/offers page** being scraped
  (prefer offer hero / promo `<img>`, then `og:image` / `twitter:image` on that
  same URL).
- Accept common raster URLs: `.png`, `.jpg`, `.jpeg`, `.webp` (and CDN URLs that
  serve those types without an extension).
- Persist on the deal as `image_url`.

### 2. Fallback photo from elsewhere on the site

- If the deal page has **no usable deal photo**, crawl/search the same merchant
  website (homepage / landing page / menu landing) for a suitable content photo
  (`img` / png / jpg / webp).
- Prefer large content images over icons, sprites, pixels, or tracking GIFs.

### 3. Dish-category generic (last resort)

- `resolve_dish_placeholder(..., discover_unknown=True)` — match dish keywords /
  venue defaults; learn new dish types (e.g. tagine) and persist for future scrapes.

### 3. Company logo

- Separately extract the **company logo** (e.g. Nando’s chicken logo):
  `link[rel~=icon]`, apple-touch-icon, header logo `<img>`
  (`alt`/`class`/`id` containing logo/brand), or clear logo asset URLs.
- Persist as `logo_url` on the merchant (or scraped deal payload → merchant),
  distinct from the deal hero `image_url`.
- Logos must not replace the deal photo.

### 4. Deal page UI — circular logo insert

On the MealDeals **deal detail page** (and deal cards if practical), render:

- Main deal image = scraped `image_url` (steps 1–2).
- Company logo = circular insert overlaid at the **bottom-left** of the main deal
  image (`rounded-full`, small avatar, slight border/contrast so it reads on
  photos).
- If `logo_url` is missing, omit the circle (do not invent a logo).

### Implementation touchpoints

- Scraper parse: `backend/app/scrapers/global_retail.py` (`_extract_image_url`,
  add logo extraction; stop skipping logo assets when extracting logos).
- Payload: `ScrapedDeal` + ingest so `image_url` and `logo_url` persist.
- API feed/detail must return logo for the frontend.
- UI: deal detail page + `DealCard` — circular bottom-left logo over hero image.
- After fixing image scrape logic, re-run scrape (or targeted re-ingest) so the
  website shows newest photos/logos — same website refresh rules below.

Prefer the fuller project skill when present:
`/Users/justinw/Projects/PRO4-Mealdeals/.cursor/skills/scrape/SKILL.md`
(includes category taxonomy + **Wine Farms pack** notes).

## Wine Farms & Entertainment — REQUIRED pack + tagging

Keep wine-farm coverage real on every `/scrape` (historically empty / grocery
false positives like Casino Cameroon).

1. Maintain `WINE_FARM_PACK` in
   `backend/app/scrapers/hospitality_pack.py` (merged into full-market scrapes).
2. Seed wine markets **ZA, US, AU, NZ, FR, IT, ES, PT, CL, AR, DE, GB** with
   real cellar-door / tasting-lunch URLs; merchant names must include
   vineyard / winery / wine farm / estate / cellar door / domaine / château /
   bodega / weingut / quinta tokens.
3. Sync tagging in `categories.py` + `frontend/lib/categories.ts`: prefer those
   wine tokens; never classify bare `casino` as entertainment; route grocery
   Casino brands to Deli's and Grocers.
4. Optional discovery: tourism / cellar-door lunch directories → append real F&B
   URLs to the pack, then re-scrape (no invented merchants).
5. Verify `category_tally` Wine Farms count is meaningful after the run.

## After scrape — REQUIRED website + metrics refresh

**Always** push the newest scrape into the live MealDeals website and metrics
UI before reporting to the user. Do not end `/scrape` until this is done.

1. **Keep category taxonomy in sync** so filters/cards match the scrape:
   - Backend: `backend/app/scrapers/categories.py`
   - Frontend: `frontend/lib/categories.ts`
   - If brand rules or parents changed during the scrape pass, update the
     frontend rules to match before verifying pages.
2. **Ensure the Next.js site is serving fresh data**:
   - Confirm `frontend` is up on `:3000` (`npm run dev` in `frontend/` if down).
   - Hit a sample area page (e.g. `http://localhost:3000/gb/london`) and confirm
     newly scraped merchants appear in the HTML/feed.
   - If the page looks stale, restart the frontend (`npm run dev`) and re-check.
   - Deals come from the API DB — after a successful ingest, the site must show
     that inventory; do not leave the user on old scraped data.
3. **Refresh the metrics inspection canvas** with the latest report snapshot:
   - Source: `GET /api/v1/scrapers/report` (or the scrape response `report`).
   - Update
     `~/.cursor/projects/Users-justinw-Projects-justin-bot/canvases/scrape-metrics-inspection.canvas.tsx`
     (create it if missing) with embedded newest summary, `category_tally`,
     `by_country`, and `breakdown`.
   - Open the canvas for the user.
4. **Optional but preferred:** export marketing CSV for the refreshed pass:

```bash
curl -sS 'http://localhost:8000/api/v1/marketing/contacts/export' -o marketing_contacts.csv
```

## After scrape — REQUIRED user report

Parse the JSON (`report` object, or `GET /api/v1/scrapers/report`) and **always**
render these three markdown tables to the user. Do not skip or summarize away
the breakdown tables.

### 1. Summary metrics

| Metric | Result |
|--------|--------|
| Areas | `{summary.areas}` cities |
| Markets | `{summary.markets}` countries |
| Deals discovered / ingested | `{summary.deals_discovered}` / `{summary.deals_ingested}` |
| Marketing contacts upserted | `{summary.marketing_contacts_upserted}` (`{summary.marketing_contacts_unique}` unique in DB) |
| Runtime | `{summary.runtime_seconds}`s |

### 2. Breakdown by country → city → category

Render a table from `report.breakdown` (or top-level `breakdown`):

| Country | City | Category | Deals |
|---------|------|----------|-------|
| GB | London | Restaurants, Cafe's & Bistro's | 12 |
| … | … | … | … |

Include **all** rows returned (country, city, category, deals). If the table is
very long, still show it in full (or attach via a file) — do not collapse to
country-only totals unless the user asks.

### 3. Category tally

Render a separate table from `report.category_tally`:

| Category | Deals |
|----------|-------|
| Restaurants, Cafe's & Bistro's | 240 |
| Food Trucks & Takeaway's | 180 |
| … | … |

### 4. Show

After the tables, briefly note that the website + metrics canvas were refreshed,
marketing CSV export is available, and contacts live in `marketing_contacts`
(separate from `merchants` / `deals`).

## Marketing export

- List: `GET /api/v1/marketing/contacts`
- CSV: `GET /api/v1/marketing/contacts/export`
- Live report snapshot: `GET /api/v1/scrapers/report`

```bash
curl -sS 'http://localhost:8000/api/v1/marketing/contacts/export' -o marketing_contacts.csv
```

## Verify

1. Response `status` is `completed` (or Celery log shows `Worldwide scrape complete`).
2. `markets` length matches full `TARGET_MARKETS` (not a subset).
3. Website sample page shows newest scraped merchants (not a stale feed).
4. Sample deal pages show site-sourced deal photos when available, plus circular
   bottom-left company logo when `logo_url` exists.
5. Metrics canvas reflects the latest `/api/v1/scrapers/report` totals.
6. Present the three tables above to the user.

## Do not

- Invent non-F&B merchants.
- Leave Wine Farms empty by omitting `WINE_FARM_PACK`, or tag grocery Casino
  chains as Wine Farms / Entertainment.
- Scrape only `NEW_MARKETS` / `only_new` when the user invokes `/scrape`.
- Delete marketing contacts on re-scrape (upsert / refresh only).
- Skip the results breakdown tables.
- Skip the website / metrics refresh after a successful scrape.
- Prefer stock/Unsplash placeholders when a real deal or landing-page photo
  exists on the merchant site.
- Skip force photo order (deal page → site landing → dish placeholder).
- Use one generic lunch photo for all fallbacks instead of dish-matched
  placeholders from `deal_placeholders.py`.
- Use the company logo as the main deal hero image.
- Commit or push unless the user asks.
