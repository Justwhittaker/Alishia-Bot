from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from alishia_bot.shopify_mcp.client import (
    PRODUCTS_QUERY,
    SHOP_QUERY,
    ShopifyAdminClient,
    ShopifyAdminError,
    edges_to_nodes,
)
from alishia_bot.shopify_mcp.config import ShopifyConfig
from alishia_bot.shopify_mcp.csv_import import CsvImportError
from alishia_bot.shopify_mcp.importer import import_products_from_csv


@dataclass(frozen=True)
class BotResponse:
    text: str


class AlishiaBot:
    """Rule-based starter bot. Swap in LLM or platform adapters as you grow."""

    def handle(self, message: str) -> BotResponse:
        normalized = message.strip().lower()

        if not normalized:
            return BotResponse("Say something and I'll respond.")

        if normalized in {"hi", "hello", "hey"}:
            return BotResponse("Hey — Alishia Bot is online. What can I help with?")

        if normalized in {"help", "?"}:
            return BotResponse(
                "Commands: hello, help, time, echo <text>, "
                "shop, shop products [query], "
                "shop import <csv-path> [--apply]. "
                "Edit src/alishia_bot/bot.py to add your own behavior."
            )

        if normalized == "time":
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            return BotResponse(f"The current time is {now}.")

        echo_match = re.fullmatch(r"echo\s+(.+)", normalized)
        if echo_match:
            return BotResponse(echo_match.group(1))

        if normalized == "shop" or normalized.startswith("shop "):
            return BotResponse(self._handle_shop(message.strip()))

        return BotResponse(
            f"I heard: {message.strip()}. Try `help` to see what I can do."
        )

    def _handle_shop(self, message: str) -> str:
        parts = message.split()
        subcommand = parts[1].lower() if len(parts) > 1 else "status"

        if subcommand == "import":
            return self._handle_shop_import(parts[2:])

        try:
            client = ShopifyAdminClient(ShopifyConfig.from_env())
        except ValueError as exc:
            return (
                f"{exc}\n"
                "Set SHOPIFY_STORE_DOMAIN and SHOPIFY_ACCESS_TOKEN in .env "
                "(see .env.example)."
            )

        try:
            if subcommand in {"status", "info"}:
                shop = client.execute(SHOP_QUERY).get("shop") or {}
                return (
                    f"{shop.get('name', 'Store')} — "
                    f"{shop.get('myshopifyDomain', client.store_domain)} — "
                    f"{shop.get('currencyCode', '?')} — "
                    f"plan {(shop.get('plan') or {}).get('displayName', '?')}"
                )

            if subcommand == "products":
                query = " ".join(parts[2:]) if len(parts) > 2 else ""
                variables: dict = {"first": 10}
                if query:
                    variables["query"] = query
                products = edges_to_nodes(
                    client.execute(PRODUCTS_QUERY, variables).get("products")
                )
                if not products:
                    return "No products found."
                lines = []
                for product in products:
                    price = (
                        (product.get("priceRangeV2") or {})
                        .get("minVariantPrice", {})
                        .get("amount")
                    )
                    currency = (
                        (product.get("priceRangeV2") or {})
                        .get("minVariantPrice", {})
                        .get("currencyCode", "")
                    )
                    price_bit = f" — {price} {currency}".rstrip() if price else ""
                    lines.append(
                        f"- {product.get('title')} "
                        f"[{product.get('status')}]{price_bit}"
                    )
                return "Products:\n" + "\n".join(lines)

            return (
                "Shopify commands: `shop` / `shop status`, "
                "`shop products [query]`, "
                "`shop import <csv-path> [--apply]`.\n"
                "For full tool access, use the Cursor MCP server "
                "(`python -m alishia_bot.shopify_mcp`)."
            )
        except ShopifyAdminError as exc:
            return f"Shopify API error: {exc}"

    def _handle_shop_import(self, args: list[str]) -> str:
        if not args:
            return (
                "Usage: `shop import <csv-path> [--apply]`\n"
                "Default is dry-run preview. Pass `--apply` to write via Admin API."
            )

        apply = False
        path_parts: list[str] = []
        for arg in args:
            if arg in {"--apply", "--write", "--commit"}:
                apply = True
            else:
                path_parts.append(arg)
        csv_path = " ".join(path_parts).strip()
        if not csv_path:
            return "Usage: `shop import <csv-path> [--apply]`"

        client = None
        if apply:
            try:
                client = ShopifyAdminClient(ShopifyConfig.from_env())
            except ValueError as exc:
                return (
                    f"{exc}\n"
                    "Set SHOPIFY_STORE_DOMAIN and SHOPIFY_ACCESS_TOKEN in .env "
                    "before using --apply."
                )

        try:
            result = import_products_from_csv(
                client,
                csv_path=csv_path,
                dry_run=not apply,
                update_existing=True,
            )
        except (CsvImportError, ShopifyAdminError) as exc:
            return f"CSV import error: {exc}"

        preview = result.get("products") or []
        lines = [
            result.get("message") or "Import complete.",
            f"Parsed {result.get('parsed_count')} product(s); "
            f"selected {result.get('selected_count')}.",
        ]
        for product in preview[:10]:
            lines.append(
                f"- {product.get('title')} ({product.get('handle')}) "
                f"[{product.get('status')}] "
                f"variants={product.get('variant_count')}"
            )
        if len(preview) > 10:
            lines.append(f"... and {len(preview) - 10} more")
        if apply:
            lines.append(
                json.dumps(
                    {
                        "created": len(result.get("created") or []),
                        "updated": len(result.get("updated") or []),
                        "failed": result.get("failed") or [],
                    },
                    indent=2,
                )
            )
        else:
            lines.append("Re-run with `--apply` to write these products to Shopify.")
        return "\n".join(lines)
