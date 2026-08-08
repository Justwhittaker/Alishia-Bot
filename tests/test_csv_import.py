from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from alishia_bot.shopify_mcp import server
from alishia_bot.shopify_mcp.client import ShopifyAdminClient
from alishia_bot.shopify_mcp.config import ShopifyConfig
from alishia_bot.shopify_mcp.csv_import import (
    CsvImportError,
    parse_products_csv,
    product_to_set_input,
)
from alishia_bot.shopify_mcp.importer import import_products_from_csv


FIXTURE = Path(__file__).parent / "fixtures" / "sample_products.csv"


def test_parse_groups_variants_by_handle() -> None:
    products = parse_products_csv(FIXTURE.read_text(encoding="utf-8"))
    assert len(products) == 2

    harrison = products[0]
    assert harrison.handle == "harrison"
    assert harrison.title == "Harrison"
    assert harrison.status == "ACTIVE"
    assert len(harrison.variants) == 2
    assert harrison.variants[0].sku == "HAR-STD"
    assert harrison.variants[1].price == "12.50"
    assert harrison.options[0]["name"] == "Size"
    assert harrison.options[0]["values"] == ["Standard", "Large"]
    assert harrison.image_urls

    hart = products[1]
    assert hart.status == "DRAFT"
    assert hart.tags == ["crest"]


def test_product_to_set_input_shape() -> None:
    products = parse_products_csv(FIXTURE.read_text(encoding="utf-8"))
    payload = product_to_set_input(products[0])
    assert payload["handle"] == "harrison"
    assert payload["status"] == "ACTIVE"
    assert len(payload["variants"]) == 2
    assert payload["productOptions"][0]["name"] == "Size"
    assert payload["files"][0]["originalSource"].endswith("harrison.jpg")


def test_dry_run_import_from_path() -> None:
    result = import_products_from_csv(csv_path=str(FIXTURE), dry_run=True, limit=10)
    assert result["dry_run"] is True
    assert result["parsed_count"] == 2
    assert result["created"] == []
    assert result["products"][0]["handle"] == "harrison"


def test_apply_import_calls_product_set() -> None:
    calls: list[tuple[str, dict | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        calls.append((payload["query"], payload.get("variables")))
        return httpx.Response(
            200,
            json={
                "data": {
                    "productSet": {
                        "product": {
                            "id": "gid://shopify/Product/1",
                            "title": "Harrison",
                            "handle": "harrison",
                            "status": "ACTIVE",
                        },
                        "userErrors": [],
                    }
                }
            },
        )

    client = ShopifyAdminClient(
        ShopifyConfig(store_domain="demo.myshopify.com", access_token="shpat_test"),
        transport=httpx.MockTransport(handler),
    )
    result = import_products_from_csv(
        client,
        csv_path=str(FIXTURE),
        dry_run=False,
        update_existing=True,
        limit=1,
    )
    assert result["selected_count"] == 1
    assert result["skipped_over_limit"] == 1
    assert len(result["updated"]) == 1
    assert "productSet" in calls[0][0]
    assert calls[0][1]["identifier"] == {"handle": "harrison"}


def test_mcp_tool_dry_run() -> None:
    raw = server.shopify_import_products_csv(csv_path=str(FIXTURE), dry_run=True)
    assert "harrison" in raw
    assert '"dry_run": true' in raw


def test_missing_csv_errors() -> None:
    with pytest.raises(CsvImportError, match="Provide csv_text or csv_path"):
        import_products_from_csv(dry_run=True)
