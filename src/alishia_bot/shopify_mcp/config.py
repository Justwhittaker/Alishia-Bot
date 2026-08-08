from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ShopifyConfig:
    """Credentials for the Shopify Admin GraphQL API."""

    store_domain: str
    access_token: str
    api_version: str = "2025-10"

    @property
    def graphql_url(self) -> str:
        return f"https://{self.store_domain}/admin/api/{self.api_version}/graphql.json"

    @classmethod
    def from_env(cls) -> ShopifyConfig:
        domain = (
            os.getenv("SHOPIFY_STORE_DOMAIN")
            or os.getenv("SHOPIFY_SHOP_URL")
            or os.getenv("SHOPIFY_STORE")
            or ""
        ).strip()
        token = (os.getenv("SHOPIFY_ACCESS_TOKEN") or "").strip()
        api_version = (os.getenv("SHOPIFY_API_VERSION") or "2025-10").strip()

        if domain.startswith("https://"):
            domain = domain.removeprefix("https://")
        if domain.startswith("http://"):
            domain = domain.removeprefix("http://")
        domain = domain.rstrip("/")
        if domain and "." not in domain:
            domain = f"{domain}.myshopify.com"

        if not domain:
            raise ValueError(
                "Missing SHOPIFY_STORE_DOMAIN (e.g. your-store.myshopify.com)."
            )
        if not token:
            raise ValueError(
                "Missing SHOPIFY_ACCESS_TOKEN (Admin API access token from a custom app)."
            )
        return cls(store_domain=domain, access_token=token, api_version=api_version)
