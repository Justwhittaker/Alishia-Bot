from __future__ import annotations

import pytest

from alishia_bot.shopify_mcp.config import ShopifyConfig


def test_from_env_normalizes_short_store_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "irish-family")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "shpat_test")
    monkeypatch.delenv("SHOPIFY_API_VERSION", raising=False)

    cfg = ShopifyConfig.from_env()
    assert cfg.store_domain == "irish-family.myshopify.com"
    assert cfg.access_token == "shpat_test"
    assert cfg.graphql_url.endswith("/admin/api/2025-10/graphql.json")


def test_from_env_strips_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "https://demo.myshopify.com/")
    monkeypatch.setenv("SHOPIFY_ACCESS_TOKEN", "shpat_test")

    cfg = ShopifyConfig.from_env()
    assert cfg.store_domain == "demo.myshopify.com"


def test_from_env_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHOPIFY_STORE_DOMAIN", "demo.myshopify.com")
    monkeypatch.delenv("SHOPIFY_ACCESS_TOKEN", raising=False)

    with pytest.raises(ValueError, match="SHOPIFY_ACCESS_TOKEN"):
        ShopifyConfig.from_env()
