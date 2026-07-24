"""Example auto-discovered provider: Intelligence X.

Free endpoint. To enable: set `OSINT_EXTRA_PROVIDERS=intelx`.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


class IntelXProvider(BaseProvider):
    name = "intelx"
    kind = "domain"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 15
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 10.0
    health_url = "https://intelx.io/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        data = await get_json(
            "https://2.intelx.io/intelligent/search",
            params={"k": target, "limit": 20},
        )
        if not data or not isinstance(data, dict):
            return {"found": False, "target": target}
        records = data.get("records", []) or []
        return {
            "target": target,
            "count": len(records),
            "selectors": [r.get("selector") for r in records[:10]],
            "bucket": data.get("bucket"),
        }


PROVIDER_CLASS = IntelXProvider
