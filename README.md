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

Try: `hello`, `help`, `time`, `echo your message here`, `shop`, `shop products`

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

**Storefront (public store MCP, no Admin token)**

- `storefront_search_policies`
- `storefront_update_cart`

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
