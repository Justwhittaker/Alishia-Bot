from __future__ import annotations

import json
from typing import Any

import httpx

from alishia_bot.shopify_mcp.config import ShopifyConfig


class ShopifyAdminError(RuntimeError):
    """Raised when the Shopify Admin API returns an error."""


class ShopifyAdminClient:
    """Thin GraphQL client for Shopify Admin API."""

    def __init__(
        self,
        config: ShopifyConfig,
        *,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._timeout = timeout
        self._transport = transport

    @property
    def store_domain(self) -> str:
        return self._config.store_domain

    def execute(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self._config.access_token,
        }
        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        client_kwargs: dict[str, Any] = {"timeout": self._timeout}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport

        with httpx.Client(**client_kwargs) as client:
            response = client.post(
                self._config.graphql_url, headers=headers, json=payload
            )

        if response.status_code >= 400:
            raise ShopifyAdminError(
                f"HTTP {response.status_code} from Shopify: {response.text[:500]}"
            )

        body = response.json()
        if body.get("errors"):
            raise ShopifyAdminError(
                f"GraphQL errors: {json.dumps(body['errors'], indent=2)}"
            )
        data = body.get("data")
        if data is None:
            raise ShopifyAdminError("Shopify response missing data.")
        return data


SHOP_QUERY = """
query ShopInfo {
  shop {
    name
    email
    myshopifyDomain
    primaryDomain { url host }
    currencyCode
    plan { displayName }
    timezoneAbbreviation
  }
}
"""

PRODUCTS_QUERY = """
query Products($first: Int!, $query: String) {
  products(first: $first, query: $query) {
    edges {
      node {
        id
        title
        handle
        status
        totalInventory
        productType
        vendor
        tags
        priceRangeV2 {
          minVariantPrice { amount currencyCode }
          maxVariantPrice { amount currencyCode }
        }
        featuredImage { url altText }
      }
    }
  }
}
"""

PRODUCT_BY_ID_QUERY = """
query Product($id: ID!) {
  product(id: $id) {
    id
    title
    handle
    status
    descriptionHtml
    productType
    vendor
    tags
    totalInventory
    variants(first: 50) {
      edges {
        node {
          id
          title
          sku
          price
          inventoryQuantity
          availableForSale
        }
      }
    }
  }
}
"""

PRODUCT_BY_HANDLE_QUERY = """
query ProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    handle
    status
    descriptionHtml
    productType
    vendor
    tags
    totalInventory
    variants(first: 50) {
      edges {
        node {
          id
          title
          sku
          price
          inventoryQuantity
          availableForSale
        }
      }
    }
  }
}
"""

ORDERS_QUERY = """
query Orders($first: Int!, $query: String) {
  orders(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
    edges {
      node {
        id
        name
        createdAt
        displayFinancialStatus
        displayFulfillmentStatus
        totalPriceSet { shopMoney { amount currencyCode } }
        customer { displayName email }
        lineItems(first: 10) {
          edges {
            node { title quantity }
          }
        }
      }
    }
  }
}
"""

ORDER_QUERY = """
query Order($id: ID!) {
  order(id: $id) {
    id
    name
    createdAt
    email
    phone
    displayFinancialStatus
    displayFulfillmentStatus
    note
    tags
    totalPriceSet { shopMoney { amount currencyCode } }
    shippingAddress {
      name
      address1
      address2
      city
      province
      country
      zip
    }
    customer { id displayName email }
    lineItems(first: 50) {
      edges {
        node {
          title
          quantity
          sku
          originalUnitPriceSet { shopMoney { amount currencyCode } }
        }
      }
    }
  }
}
"""

CUSTOMERS_QUERY = """
query Customers($first: Int!, $query: String) {
  customers(first: $first, query: $query) {
    edges {
      node {
        id
        displayName
        email
        phone
        numberOfOrders
        createdAt
        tags
      }
    }
  }
}
"""

PRODUCT_CREATE_MUTATION = """
mutation ProductCreate($product: ProductCreateInput!) {
  productCreate(product: $product) {
    product {
      id
      title
      handle
      status
    }
    userErrors { field message }
  }
}
"""


def edges_to_nodes(connection: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not connection:
        return []
    return [edge["node"] for edge in connection.get("edges", []) if "node" in edge]
