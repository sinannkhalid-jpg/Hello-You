"""
crt.sh provider — Certificate Transparency log search.

Public, no key. We reuse the original implementation but expose a clean
`lookup(target)` that returns both the cert list and a derived subdomain
list.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


class CrtshProvider(BaseProvider):
    name = "crtsh"
    kind = "domain"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 30
    cache_ttl = 60 * 60 * 6
    timeout_seconds = 30.0  # crt.sh can be slow
    health_url = "https://crt.sh/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        url = f"https://crt.sh/?q={target}&output=json&dedupe=Y"
        data = await get_json(url, timeout=30)
        if not data:
            return {"certificates": [], "subdomains": []}
        if not isinstance(data, list):
            return {"certificates": [], "subdomains": [], "error": "unexpected response"}

        limit = int(kwargs.get("limit", 100))
        certs: list[dict[str, Any]] = []
        for row in data[:limit]:
            certs.append(
                {
                    "id": row.get("id"),
                    "issuer_name": row.get("issuer_name"),
                    "common_name": row.get("common_name"),
                    "name_value": row.get("name_value"),
                    "not_before": row.get("not_before"),
                    "not_after": row.get("not_after"),
                    "serial_number": row.get("serial_number"),
                }
            )
        # Derive subdomains
        sub_set: set[str] = set()
        for c in certs:
            for n in (c.get("name_value") or "").splitlines():
                n = n.strip().lower().lstrip("*.")
                if n.endswith("." + target) or n == target:
                    sub_set.add(n)
        return {
            "certificates": certs,
            "subdomains": sorted(sub_set),
            "count": len(certs),
        }
