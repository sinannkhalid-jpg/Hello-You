"""
RDAP / WHOIS provider.

Uses IANA's RDAP bootstrap to find the right registry, then queries.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json
from app.osint.whois_provider import rdap_lookup, summarize_rdap  # type: ignore


class WhoisProvider(BaseProvider):
    name = "whois"
    kind = "domain"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 60
    cache_ttl = 60 * 60 * 12
    timeout_seconds = 8.0
    health_url = "https://data.iana.org/rdap/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        data = await rdap_lookup(target)
        if not data:
            return {"source": "rdap", "error": "no RDAP endpoint or no data"}
        return summarize_rdap(data)
