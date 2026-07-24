"""
Shared async HTTP client helpers for providers.

We use httpx.AsyncClient. Each call gets a fresh client (cheap in httpx)
so providers don't share connection state.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
DEFAULT_HEADERS = {
    "User-Agent": "HelloYou/1.0 (+educational)",
    "Accept": "application/json",
}


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
) -> dict[str, Any] | list[Any] | None:
    """GET a JSON resource. Returns None on failure."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout or DEFAULT_TIMEOUT,
            headers={**DEFAULT_HEADERS, **(headers or {})},
            follow_redirects=True,
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            try:
                return r.json()
            except json.JSONDecodeError:
                return None
    except httpx.HTTPError:
        return None


async def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
) -> str | None:
    try:
        async with httpx.AsyncClient(
            timeout=timeout or DEFAULT_TIMEOUT,
            headers={**DEFAULT_HEADERS, **(headers or {})},
            follow_redirects=True,
        ) as client:
            r = await client.get(url, params=params)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.text
    except httpx.HTTPError:
        return None
