from __future__ import annotations

import httpx
import pytest

from alishia_bot.shopify_mcp.client import ShopifyAdminClient, ShopifyAdminError
from alishia_bot.shopify_mcp.config import ShopifyConfig


def test_execute_returns_data() -> None:
    cfg = ShopifyConfig(
        store_domain="demo.myshopify.com",
        access_token="shpat_test",
        api_version="2025-10",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Shopify-Access-Token"] == "shpat_test"
        assert str(request.url).endswith("/admin/api/2025-10/graphql.json")
        return httpx.Response(200, json={"data": {"shop": {"name": "Demo"}}})

    client = ShopifyAdminClient(cfg, transport=httpx.MockTransport(handler))
    data = client.execute("{ shop { name } }")
    assert data == {"shop": {"name": "Demo"}}


def test_execute_raises_on_graphql_errors() -> None:
    cfg = ShopifyConfig(
        store_domain="demo.myshopify.com",
        access_token="shpat_test",
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json={"errors": [{"message": "Access denied"}]}
        )
    )
    client = ShopifyAdminClient(cfg, transport=transport)

    with pytest.raises(ShopifyAdminError, match="Access denied"):
        client.execute("{ shop { name } }")
