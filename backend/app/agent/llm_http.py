"""HTTP client helpers for OpenAI-compatible LLM providers."""

from __future__ import annotations

from typing import Any

import httpx


def direct_http_clients() -> dict[str, Any]:
    """Build clients that ignore ambient proxy settings.

    The Token Plan endpoint must be reached directly. Keeping `trust_env=False`
    prevents httpx/OpenAI from picking up Windows or shell proxy settings.
    """
    return {
        "http_client": httpx.Client(trust_env=False),
        "http_async_client": httpx.AsyncClient(trust_env=False),
    }
