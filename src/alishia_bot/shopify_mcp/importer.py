from __future__ import annotations

from typing import Any

from alishia_bot.shopify_mcp.client import (
    PRODUCT_SET_MUTATION,
    ShopifyAdminClient,
    ShopifyAdminError,
)
from alishia_bot.shopify_mcp.csv_import import (
    CsvImportError,
    ParsedProduct,
    load_csv_text,
    parse_products_csv,
    parsed_product_summary,
    product_to_set_input,
)


DEFAULT_IMPORT_LIMIT = 50
MAX_IMPORT_LIMIT = 200


def import_products_from_csv(
    client: ShopifyAdminClient | None = None,
    *,
    csv_text: str = "",
    csv_path: str = "",
    dry_run: bool = True,
    update_existing: bool = True,
    limit: int = DEFAULT_IMPORT_LIMIT,
) -> dict[str, Any]:
    """Parse a Shopify product CSV and optionally upsert products via productSet."""
    text = load_csv_text(csv_text=csv_text, csv_path=csv_path)
    products = parse_products_csv(text)

    capped_limit = max(1, min(int(limit), MAX_IMPORT_LIMIT))
    selected = products[:capped_limit]
    skipped = len(products) - len(selected)

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "update_existing": update_existing,
        "parsed_count": len(products),
        "selected_count": len(selected),
        "skipped_over_limit": skipped,
        "limit": capped_limit,
        "products": [parsed_product_summary(product) for product in selected],
        "created": [],
        "updated": [],
        "failed": [],
    }

    if dry_run:
        result["message"] = (
            "Dry run only — no Admin API writes. Re-run with dry_run=false to import."
        )
        return result

    if client is None:
        raise CsvImportError("Admin client is required when dry_run=false.")

    for product in selected:
        try:
            outcome = _upsert_product(client, product, update_existing=update_existing)
        except (ShopifyAdminError, CsvImportError) as exc:
            result["failed"].append(
                {"handle": product.handle, "title": product.title, "error": str(exc)}
            )
            continue

        bucket = result["updated"] if outcome["action"] == "updated" else result["created"]
        bucket.append(outcome)

    result["message"] = (
        f"Import finished: {len(result['created'])} created, "
        f"{len(result['updated'])} updated, {len(result['failed'])} failed."
    )
    return result


def _upsert_product(
    client: ShopifyAdminClient,
    product: ParsedProduct,
    *,
    update_existing: bool,
) -> dict[str, Any]:
    variables: dict[str, Any] = {
        "synchronous": True,
        "input": product_to_set_input(product),
    }
    action = "created"
    if update_existing:
        variables["identifier"] = {"handle": product.handle}
        action = "upserted"

    data = client.execute(PRODUCT_SET_MUTATION, variables)
    payload = data.get("productSet") or {}
    errors = payload.get("userErrors") or []
    if errors:
        raise CsvImportError(
            "; ".join(
                f"{'.'.join(err.get('field') or [])}: {err.get('message')}"
                if err.get("field")
                else str(err.get("message"))
                for err in errors
            )
        )

    remote = payload.get("product") or {}
    # productSet with identifier updates; without creates. When update_existing,
    # treat as upsert (caller buckets as updated for visibility).
    if update_existing:
        action = "updated"
    return {
        "action": action,
        "id": remote.get("id"),
        "handle": remote.get("handle") or product.handle,
        "title": remote.get("title") or product.title,
        "status": remote.get("status") or product.status,
    }
