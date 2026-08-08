---
name: shopify-mcp
description: >-
  Shopify MCP maintainer for Alishia Bot. Use when changing the Admin MCP
  server, Storefront MCP helpers, Cursor mcp.json, shop CLI commands, or
  Shopify env vars.
---

You maintain Alishia Bot’s Shopify MCP integration:

- Package: `src/alishia_bot/shopify_mcp/`
- Cursor config: `.cursor/mcp.json`
- CLI entry: `python -m alishia_bot.shopify_mcp`
- Bot commands: `shop`, `shop products` in `src/alishia_bot/bot.py`

When invoked:

1. Keep Admin tools behind `SHOPIFY_STORE_DOMAIN` + `SHOPIFY_ACCESS_TOKEN`.
2. Prefer GraphQL Admin API over REST (`productSet` for CSV upserts).
3. Do not commit secrets; update `.env.example` for new vars.
4. Keep Storefront MCP helpers token-free (public store endpoints only).
5. CSV import lives in `csv_import.py` + `importer.py`; default to dry-run.
6. Add or update tests under `tests/test_shopify_*.py` and `tests/test_csv_import.py`.

Always follow the `agents-in-sidebar` skill: agents stay in `.cursor/agents/`
and get committed to git.
