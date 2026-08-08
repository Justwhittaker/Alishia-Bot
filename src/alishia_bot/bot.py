from __future__ import annotations

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
                "shop, shop products [query]. "
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
        parts = message.split(maxsplit=2)
        subcommand = parts[1].lower() if len(parts) > 1 else "status"

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
                query = parts[2] if len(parts) > 2 else ""
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
                "`shop products [query]`.\n"
                "For full tool access, use the Cursor MCP server "
                "(`python -m alishia_bot.shopify_mcp`)."
            )
        except ShopifyAdminError as exc:
            return f"Shopify API error: {exc}"
