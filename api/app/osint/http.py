"""Shared async HTTP client with sane defaults and retries."""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
DEFAULT_HEADERS = {
    "User-Agent": "OSINT-Nexus/1.0 (+educational-use)",
    "Accept": "application/json",
}


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    retries: int = 2,
) -> dict[str, Any] | list[Any] | None:
    """GET with retry/backoff. Returns None on persistent failure."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=timeout or DEFAULT_TIMEOUT,
                headers={**DEFAULT_HEADERS, **(headers or {})},
                follow_redirects=True,
            ) as client:
                r = await client.get(url, params=params)
                if r.status_code == 429:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "server error", request=r.request, response=r
                    )
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.json()
        except (httpx.HTTPError, httpx.RequestError) as e:
            last_exc = e
            await asyncio.sleep(0.5 * (attempt + 1))
    log.warning("GET %s failed after %d attempts: %s", url, retries + 1, last_exc)
    return None


async def get_text(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    retries: int = 2,
) -> str | None:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
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
        except (httpx.HTTPError, httpx.RequestError) as e:
            last_exc = e
            await asyncio.sleep(0.5 * (attempt + 1))
    log.warning("GET(text) %s failed: %s", url, last_exc)
    return None
