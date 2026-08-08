# Alishia Bot

A personal Python bot starter. Lives under `~/Projects/JustinBot/` next to `justin-bot/` and `MealDeals/`.

## Quick start

```bash
cd ~/Projects/JustinBot/Alishia-Bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Try: `hello`, `help`, `time`, `echo your message here`, `shop`, `shop products`, `shop import path/to.csv`

## Shopify app (`alishia-app`)

Scaffolded with `npm init @shopify/app@latest` (React Router template).

```bash
cd alishia-app
shopify app dev
```

Linked Dev Dashboard app: **alishia-app** (`client_id` in `alishia-app/shopify.app.toml`).

## Shopify MCP

Alishia Bot ships a **Shopify Admin MCP server** for Cursor (and any MCP client), plus optional CLI shop commands.

### 1. Create a Shopify custom app token

1. In Shopify Admin: **Settings → Apps and sales channels → Develop apps**
2. Allow custom app development if prompted
3. Create an app (e.g. `Alishia MCP`)
4. Configure Admin API scopes (start with):
   - `read_products`, `write_products`
   - `read_orders`
   - `read_customers`
5. Install the app and copy the **Admin API access token** (`shpat_...`)

### 2. Configure env

```bash
cp .env.example .env
# edit .env with your store domain + token
```

### 3. Use in Cursor

Project MCP config lives at `.cursor/mcp.json` and registers:

| Server | Purpose |
|--------|---------|
| `shopify` | This repo’s Admin + Storefront MCP tools |
| `shopify-dev-mcp` | Official Shopify docs / schema / validation (`@shopify/dev-mcp`) |

Restart Cursor (or reload MCP servers), then ask things like:

- “What Shopify tools do you have?”
- “List my 10 most recent products”
- “Show unpaid orders”
- “Create a draft product titled Harrison Crest”

Run the server manually:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m alishia_bot.shopify_mcp
```

### Available MCP tools

**Admin (requires token)**

- `shopify_get_shop`
- `shopify_search_products`
- `shopify_get_product`
- `shopify_list_orders`
- `shopify_get_order`
- `shopify_search_customers`
- `shopify_create_product`
- `shopify_import_products_csv` — Shopify-style product CSV upsert via `productSet`

**Storefront (public store MCP, no Admin token)**

- `storefront_search_policies`
- `storefront_update_cart`

### CSV product import

Uses Shopify product-export columns (`Handle`, `Title`, `Body (HTML)`, `Vendor`, `Type`, `Tags`, `OptionN Name/Value`, `Variant Price`, `Variant SKU`, `Image Src`, `Status` / `Published`, …). Rows with the same `Handle` become one product with multiple variants.

**MCP (recommended)**

1. Call `shopify_import_products_csv` with `csv_path` or `csv_text` and `dry_run=true`
2. Review the parsed product summary
3. Re-run with `dry_run=false` (needs `write_products`)

**CLI**

```bash
# preview
# in the bot: shop import tests/fixtures/sample_products.csv
# write:
# shop import tests/fixtures/sample_products.csv --apply
```

Notes:

- Default limit is 50 products per run (max 200)
- `update_existing=true` upserts by handle
- Inventory quantities / location stocking are not written yet (price, SKU, options, images, status are)
- This is API upsert, not Shopify Admin’s browser “Import CSV” button

## Project layout

```
Alishia-Bot/
├── run.py
├── requirements.txt
├── .env.example
├── .cursor/
│   ├── agents/          # Agents sidebar entries
│   └── mcp.json         # Shopify MCP servers for Cursor
├── tests/
└── src/alishia_bot/
    ├── bot.py
    ├── main.py
    └── shopify_mcp/     # Admin + Storefront MCP server
```

## Tests

```bash
source .venv/bin/activate
PYTHONPATH=src pytest -q
```

## License

MIT
