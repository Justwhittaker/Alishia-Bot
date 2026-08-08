from __future__ import annotations

import json

import pytest

from alishia_bot.shopify_mcp import server


class FakeClient:
    def __init__(self, data: dict) -> None:
        self._data = data
        self.calls: list[tuple[str, dict | None]] = []

    def execute(self, query: str, variables: dict | None = None) -> dict:
        self.calls.append((query, variables))
        return self._data


def test_shopify_search_products_formats_edges(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeClient(
        {
            "products": {
                "edges": [
                    {"node": {"id": "gid://shopify/Product/1", "title": "Harrison"}},
                ]
            }
        }
    )
    monkeypatch.setattr(server, "_client", lambda: fake)

    raw = server.shopify_search_products(query="Harrison", limit=5)
    payload = json.loads(raw)
    assert payload["count"] == 1
    assert payload["products"][0]["title"] == "Harrison"
    assert fake.calls[0][1] == {"first": 5, "query": "Harrison"}


def test_shopify_get_product_requires_id_or_handle() -> None:
    assert server.shopify_get_product() == "Error: Provide product_id or handle."


def test_shopify_create_product_rejects_bad_status() -> None:
    assert "ACTIVE, DRAFT, or ARCHIVED" in server.shopify_create_product(
        title="Crest", status="LIVE"
    )
