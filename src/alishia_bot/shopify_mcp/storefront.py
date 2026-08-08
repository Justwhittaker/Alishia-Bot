from __future__ import annotations

import json
from typing import Any

import httpx


class StorefrontMcpError(RuntimeError):
    """Raised when a Storefront MCP call fails."""


def _normalize_store_domain(store_domain: str) -> str:
    domain = store_domain.strip()
    if domain.startswith("https://"):
        domain = domain.removeprefix("https://")
    if domain.startswith("http://"):
        domain = domain.removeprefix("http://")
    domain = domain.rstrip("/")
    if domain and "." not in domain:
        domain = f"{domain}.myshopify.com"
    return domain


def call_storefront_mcp(
    store_domain: str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    timeout: float = 30.0,
) -> Any:
    """Call a store's public Storefront MCP endpoint (no Admin token required)."""
    domain = _normalize_store_domain(store_domain)
    if not domain:
        raise StorefrontMcpError("store_domain is required.")

    url = f"https://{domain}/api/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
        )
    if response.status_code >= 400:
        raise StorefrontMcpError(
            f"HTTP {response.status_code} from Storefront MCP: {response.text[:500]}"
        )
    body = response.json()
    if "error" in body:
        raise StorefrontMcpError(json.dumps(body["error"], indent=2))
    return body.get("result")
