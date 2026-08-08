---
name: metric_monitor
description: >-
  Fetches live MealDeals scrape metrics from the local API, refreshes the
  scrape-metrics-inspection canvas with summary, category tally, and a
  Country → City → Category drill-down (full country/city names, percentage
  shares), MUST open the canvas in the IDE via cursor-app-control open_resource
  (never only write the file), and posts a brief chat summary. Use when the user
  invokes /metric_monitor or asks for scrape metrics, metrics canvas, metric
  monitor, category tally, country city drill-down, or to inspect scrape report
  numbers.
disable-model-invocation: false
---

# /metric_monitor — MealDeals scrape metrics canvas

Canonical command: **`/metric_monitor`**. Auto-invoke this skill whenever Justin
asks for scrape metrics / metrics canvas / metric monitor / category tally /
country→city drill-down — do not wait for the slash command.

## Paths

| Role | Path |
|------|------|
| Project root | `/Users/justinw/Projects/PRO4-Mealdeals` (symlink → JustinBot/MealDeals) |
| Backend compose | `/Users/justinw/Projects/PRO4-Mealdeals/backend` |
| Report API | `GET http://localhost:8000/api/v1/scrapers/report` |
| Canvas | `/Users/justinw/.cursor/projects/Users-justinw-Projects-justin-bot/canvases/scrape-metrics-inspection.canvas.tsx` |

Also read `~/.cursor/skills-cursor/canvas/SKILL.md` before editing the canvas.

## Workflow

Copy and track:

```
Metric monitor:
- [ ] 1. Ensure API is up
- [ ] 2. Fetch live report
- [ ] 3. Refresh canvas (embed data + drill-down)
- [ ] 4. MUST open canvas via open_resource (required final step)
- [ ] 5. Brief chat summary + markdown canvas link
```

**Hard requirement:** Step 4 is mandatory on every `/metric_monitor` run.
Do **not** just write the canvas file and tell Justin to open it. Always call
`open_resource` so the canvas is shown in the IDE automatically before the turn
ends.

### 1. Ensure API is up

```bash
curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/scrapers/report
```

If not `200`, start backend:

```bash
cd /Users/justinw/Projects/PRO4-Mealdeals/backend && docker compose up -d
```

Wait until the report endpoint returns 200 (retry a few seconds).

### 2. Fetch live report

```bash
curl -sS http://localhost:8000/api/v1/scrapers/report
```

Expected JSON shape (snake_case from API):

- `summary` — `areas`, `markets`, `deals_discovered`, `deals_ingested`, `marketing_contacts_upserted`, `marketing_contacts_unique`, `runtime_seconds`, `active_deals_in_db`, optional `market_codes`
- `by_country` — `{ "GB": 123, ... }` (ISO codes)
- `category_tally` — `[{ "category", "deals" }, ...]`
- `breakdown` — `[{ "country", "city", "category", "deals" }, ...]` (may be ~1700 rows)

### 3. Refresh the canvas

Overwrite the canvas file at the path above. Keep the interactive inspector pattern
(filters + charts + drill-down). Embed a single `const REPORT = { ... }` object
**inline** (no `fetch()`, no network in the canvas).

Map API → canvas `REPORT` (camelCase inside the canvas):

```ts
const REPORT = {
  summary: {
    areas, markets, deals_discovered, deals_ingested,
    marketing_contacts_upserted, marketing_contacts_unique,
    runtime_seconds, active_deals_in_db, market_codes?,
  },
  byCountry: { /* ISO → deals */ },
  categoryTally: [{ category, deals }],
  topCountries: [{ country: "GB", deals }], // top ~15 by deals
  breakdown: [{ country, city, category, deals }],
  countryNames: { GB: "United Kingdom", /* … */ },
};
```

**Country labels (required):** build `countryNames` for every ISO code in
`by_country` / `breakdown`. UI must show **full English country names** in:

- Country `Select` option labels (values stay ISO codes)
- Collapsible country titles
- Bar chart category labels

Keep filter **values** as ISO codes (e.g. `GB`). Generate names with Node:

```bash
node -e '
const codes = ["GB","US"]; // all codes from report
const dn = new Intl.DisplayNames(["en"], { type: "region" });
console.log(JSON.stringify(Object.fromEntries(codes.map(c => [c, dn.of(c) || c]))));
'
```

**City labels (required):** never show raw slugs in UI. Title-case human names
(`new-york` → `New York`, underscores/hyphens → spaces; keep USA/UK/UAE; `st` → `St.`).

**Drill-down (required):** collapsed `Country → City → Category` with percentages:

| Level | Trailing / columns |
|-------|--------------------|
| Country | `{deals} deals · {x}% of view` (share of filtered deal total) |
| City | `{deals} · {x}% of {CountryName}` |
| City expand | table: Category / Deals / Share of city |

Use `CollapsibleSection` from `cursor/canvas`. Default closed except when a
single country is in view.

Preserve filters (`useCanvasState` for country + category), pie chart (category
mix), bar chart (top markets / single market), and category tally table for the
active filter. Import only from `cursor/canvas`. Default-export the page
component. Omit empty sections — never fake zeroed charts.

Reuse the existing helper structure in the canvas file when present
(`countryName`, `cityName`, `LocationDrilldown`, `shareLabel`, etc.) — refresh
`REPORT` data and keep the UX.

### 4. MUST open the canvas in the IDE (required final step)

After refreshing/writing the canvas at
`/Users/justinw/.cursor/projects/Users-justinw-Projects-justin-bot/canvases/scrape-metrics-inspection.canvas.tsx`,
you **MUST** immediately open it via the cursor-app-control MCP tool
`open_resource`. This is a **required final step** — do it **before** ending the
turn. It is **not optional**.

**Do not** just write the file and tell the user to open it. **Always** call
`open_resource`.

1. Discover schema if needed: `GetMcpTools` for server `cursor-app-control`,
   tool `open_resource`.
2. Then call:

```
CallMcpTool server=cursor-app-control toolName=open_resource
arguments: {
  "uri": "file:///Users/justinw/.cursor/projects/Users-justinw-Projects-justin-bot/canvases/scrape-metrics-inspection.canvas.tsx"
}
```

3. Also include this markdown link in the chat response:

[scrape metrics](/Users/justinw/.cursor/projects/Users-justinw-Projects-justin-bot/canvases/scrape-metrics-inspection.canvas.tsx)

Skip ending the turn until `open_resource` has been invoked successfully (or
retried after auth if the MCP server needs it).

### 5. Chat summary (brief)

Show **only**:

1. Summary table — Areas, Markets, Deals discovered/ingested, Marketing contacts
   upserted (+ unique DB count), Runtime, Active deals in DB
2. Category tally table — Category → Deals (and optional %)

Do **not** dump the full Country→City→Category breakdown in chat (often ~1700
rows). Point Justin to the canvas / file for the interactive drill-down.

## Rules

- This skill **inspects** metrics; it does **not** start a new scrape (use `/scrape` for that).
- Prefer live API data over stale canvas embeds.
- If the API is unreachable after compose up, say so and stop — do not invent metrics.
- Keep the canvas under the justin-bot project canvases path above (IDE discovery).
- **Always** refresh the canvas, then **always** call `open_resource` with the
  `file://…/scrape-metrics-inspection.canvas.tsx` URI so the canvas is shown in
  the IDE without Justin clicking the file. Writing the file alone is incomplete.
- Auto-invocation stays enabled (`disable-model-invocation: false`).
