"""
LeakCheck provider.

Endpoint: https://leakcheck.io/api/public
Auth: optional `LEAKCHECK_API_KEY` (raises rate limit).

We only call LeakCheck for email-shaped or username-shaped targets.
The endpoint returns a list of sources; we normalize to a count + sample.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json
from app.services.providers.types import normalize_reputation


class LeakCheckProvider(BaseProvider):
    name = "leakcheck"
    kind = "email"  # also handles usernames
    enabled = True
    requires_key = False
    rate_limit_per_minute = 20
    cache_ttl = 60 * 60 * 24  # 24h
    timeout_seconds = 10.0
    health_url = "https://leakcheck.io/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        url = f"https://leakcheck.io/api/public?check={target}"
        data = await get_json(
            url,
            headers={"X-API-Key": self.api_key} if self.api_key else None,
        )
        if not data or not isinstance(data, dict):
            return {
                "found": False,
                "sources": [],
                "score": 0,
                "threat_level": "unknown",
            }
        if not data.get("success", False):
            # Quota, rate-limited, or not found.
            return {
                "found": False,
                "sources": [],
                "score": 0,
                "threat_level": "unknown",
                "extra": {"message": data.get("error", "no data")},
            }
        sources = data.get("sources") or []
        found = bool(data.get("found"))
        score = min(100, len(sources) * 10) if found else 0
        rep = normalize_reputation(
            suspicious=len(sources) if found else 0,
            score=score,
            extra={"sources_sample": sources[:5], "total_sources": len(sources)},
        )
        return {"found": found, **rep, "sources": sources[:10]}
