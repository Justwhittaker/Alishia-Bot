from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from alishia_bot.shopify_mcp.client import (
    CUSTOMERS_QUERY,
    ORDER_QUERY,
    ORDERS_QUERY,
    PRODUCT_BY_HANDLE_QUERY,
    PRODUCT_BY_ID_QUERY,
    PRODUCT_CREATE_MUTATION,
    PRODUCTS_QUERY,
    SHOP_QUERY,
    ShopifyAdminClient,
    ShopifyAdminError,
    edges_to_nodes,
)
from alishia_bot.shopify_mcp.config import ShopifyConfig
from alishia_bot.shopify_mcp.csv_import import CsvImportError
from alishia_bot.shopify_mcp.importer import import_products_from_csv
from alishia_bot.shopify_mcp.storefront import (
    StorefrontMcpError,
    call_storefront_mcp,
)

mcp = FastMCP(
    "shopify",
    instructions=(
        "Shopify MCP for Alishia Bot. Admin tools need SHOPIFY_STORE_DOMAIN and "
        "SHOPIFY_ACCESS_TOKEN. Use shopify_import_products_csv for Shopify-style "
        "product CSV upserts (dry_run first). Storefront tools can target any "
        "public Shopify store domain without an Admin token."
    ),
)


def _client() -> ShopifyAdminClient:
    return ShopifyAdminClient(ShopifyConfig.from_env())


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _normalize_product_gid(product_id: str) -> str:
    value = product_id.strip()
    if value.isdigit():
        return f"gid://shopify/Product/{value}"
    return value


def _normalize_order_gid(order_id: str) -> str:
    value = order_id.strip()
    if value.isdigit():
        return f"gid://shopify/Order/{value}"
    if value.startswith("#"):
        return value
    return value


@mcp.tool()
def shopify_get_shop() -> str:
    """Return shop name, domain, currency, plan, and timezone for the connected store."""
    try:
        data = _client().execute(SHOP_QUERY)
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"
    return _dump(data.get("shop"))


@mcp.tool()
def shopify_search_products(query: str = "", limit: int = 10) -> str:
    """Search products in the Shopify Admin catalog.

    Args:
        query: Shopify product search query (title, sku, tag, status, etc.).
            Empty string returns the most recent products.
        limit: Max products to return (1-50).
    """
    first = max(1, min(limit, 50))
    variables: dict[str, Any] = {"first": first}
    if query.strip():
        variables["query"] = query.strip()
    try:
        data = _client().execute(PRODUCTS_QUERY, variables)
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"
    products = edges_to_nodes(data.get("products"))
    return _dump({"count": len(products), "products": products})


@mcp.tool()
def shopify_get_product(product_id: str = "", handle: str = "") -> str:
    """Get a product by Admin GraphQL ID or handle.

    Args:
        product_id: Product GID (gid://shopify/Product/123) or numeric ID.
        handle: Product handle/slug (used when product_id is empty).
    """
    if not product_id.strip() and not handle.strip():
        return "Error: Provide product_id or handle."

    try:
        client = _client()
        if product_id.strip():
            data = client.execute(
                PRODUCT_BY_ID_QUERY, {"id": _normalize_product_gid(product_id)}
            )
            product = data.get("product")
        else:
            data = client.execute(
                PRODUCT_BY_HANDLE_QUERY, {"handle": handle.strip()}
            )
            product = data.get("productByHandle")
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"

    if not product:
        return "Error: Product not found."
    if "variants" in product:
        product = {
            **product,
            "variants": edges_to_nodes(product.get("variants")),
        }
    return _dump(product)


@mcp.tool()
def shopify_list_orders(query: str = "", limit: int = 10) -> str:
    """List recent orders, optionally filtered by Shopify order search syntax.

    Args:
        query: Order search query (e.g. financial_status:paid, email:...).
        limit: Max orders to return (1-50).
    """
    first = max(1, min(limit, 50))
    variables: dict[str, Any] = {"first": first}
    if query.strip():
        variables["query"] = query.strip()
    try:
        data = _client().execute(ORDERS_QUERY, variables)
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"

    orders = []
    for order in edges_to_nodes(data.get("orders")):
        orders.append(
            {
                **order,
                "lineItems": edges_to_nodes(order.get("lineItems")),
            }
        )
    return _dump({"count": len(orders), "orders": orders})


@mcp.tool()
def shopify_get_order(order_id: str) -> str:
    """Get a single order by Admin GraphQL ID or numeric ID.

    Args:
        order_id: Order GID (gid://shopify/Order/123) or numeric ID.
    """
    gid = _normalize_order_gid(order_id)
    if not gid.startswith("gid://"):
        return (
            "Error: Provide a numeric order ID or full GID "
            "(name lookups like #1001 are not supported here)."
        )
    try:
        data = _client().execute(ORDER_QUERY, {"id": gid})
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"
    order = data.get("order")
    if not order:
        return "Error: Order not found."
    order = {**order, "lineItems": edges_to_nodes(order.get("lineItems"))}
    return _dump(order)


@mcp.tool()
def shopify_search_customers(query: str = "", limit: int = 10) -> str:
    """Search customers by email, name, phone, or Shopify customer query syntax.

    Args:
        query: Customer search query. Empty returns recent customers.
        limit: Max customers to return (1-50).
    """
    first = max(1, min(limit, 50))
    variables: dict[str, Any] = {"first": first}
    if query.strip():
        variables["query"] = query.strip()
    try:
        data = _client().execute(CUSTOMERS_QUERY, variables)
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"
    customers = edges_to_nodes(data.get("customers"))
    return _dump({"count": len(customers), "customers": customers})


@mcp.tool()
def shopify_create_product(
    title: str,
    description_html: str = "",
    product_type: str = "",
    vendor: str = "",
    status: str = "DRAFT",
    tags: str = "",
) -> str:
    """Create a product in the connected Shopify store (Admin API).

    Args:
        title: Product title (required).
        description_html: HTML description.
        product_type: Product type / category label.
        vendor: Vendor name.
        status: ACTIVE, DRAFT, or ARCHIVED.
        tags: Comma-separated tags.
    """
    normalized_status = status.strip().upper() or "DRAFT"
    if normalized_status not in {"ACTIVE", "DRAFT", "ARCHIVED"}:
        return "Error: status must be ACTIVE, DRAFT, or ARCHIVED."

    product_input: dict[str, Any] = {
        "title": title.strip(),
        "status": normalized_status,
    }
    if description_html.strip():
        product_input["descriptionHtml"] = description_html
    if product_type.strip():
        product_input["productType"] = product_type.strip()
    if vendor.strip():
        product_input["vendor"] = vendor.strip()
    if tags.strip():
        product_input["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    try:
        data = _client().execute(
            PRODUCT_CREATE_MUTATION, {"product": product_input}
        )
    except (ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"

    payload = data.get("productCreate") or {}
    errors = payload.get("userErrors") or []
    if errors:
        return _dump({"userErrors": errors})
    return _dump(payload.get("product"))


@mcp.tool()
def shopify_import_products_csv(
    csv_text: str = "",
    csv_path: str = "",
    dry_run: bool = True,
    update_existing: bool = True,
    limit: int = 50,
) -> str:
    """Import products from a Shopify-style product CSV via Admin productSet.

    Accepts either inline CSV text or a local file path. Defaults to dry_run=true
    so you can preview parsed products before writing. Rows are grouped by Handle;
    variants/options/images follow Shopify's product export columns
    (Title, Body (HTML), Vendor, Type, Tags, OptionN Name/Value, Variant Price,
    Variant SKU, Image Src, Status/Published, etc.).

    Args:
        csv_text: Raw CSV contents (Shopify product export format or compatible).
        csv_path: Absolute/relative path to a CSV file (used when csv_text is empty).
        dry_run: If true (default), parse/preview only — no Admin writes.
        update_existing: If true, upsert by handle; if false, create without identifier.
        limit: Max products to import (1-200, default 50).
    """
    try:
        result = import_products_from_csv(
            None if dry_run else _client(),
            csv_text=csv_text,
            csv_path=csv_path,
            dry_run=dry_run,
            update_existing=update_existing,
            limit=limit,
        )
    except (CsvImportError, ShopifyAdminError, ValueError) as exc:
        return f"Error: {exc}"
    return _dump(result)


@mcp.tool()
def storefront_search_policies(
    store_domain: str,
    query: str,
) -> str:
    """Ask a store's public Storefront MCP about policies and FAQs (no Admin token).

    Args:
        store_domain: Store domain, e.g. your-store.myshopify.com.
        query: Policy or FAQ question.
    """
    try:
        result = call_storefront_mcp(
            store_domain,
            "search_shop_policies_and_faqs",
            {"query": query},
        )
    except StorefrontMcpError as exc:
        return f"Error: {exc}"
    return _dump(result)


@mcp.tool()
def storefront_update_cart(
    store_domain: str,
    add_items_json: str,
    cart_id: str = "",
) -> str:
    """Create or update a cart via a store's public Storefront MCP (no Admin token).

    Args:
        store_domain: Store domain, e.g. your-store.myshopify.com.
        add_items_json: JSON array of items, each with merchandise_id and quantity.
        cart_id: Existing cart ID. Omit to create a new cart.
    """
    try:
        items = json.loads(add_items_json)
    except json.JSONDecodeError as exc:
        return f"Error: add_items_json must be valid JSON ({exc})."
    if not isinstance(items, list):
        return "Error: add_items_json must be a JSON array."

    arguments: dict[str, Any] = {"add_items": items}
    if cart_id.strip():
        arguments["cart_id"] = cart_id.strip()
    try:
        result = call_storefront_mcp(store_domain, "update_cart", arguments)
    except StorefrontMcpError as exc:
        return f"Error: {exc}"
    return _dump(result)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
