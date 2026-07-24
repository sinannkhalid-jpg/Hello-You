"""
Shodan provider.

Reference: https://developer.shodan.io/

Authentication: `?key=...` query param. Free tier is limited to a few
endpoints; we use the most useful one (`/shodan/host/{ip}`) and degrade
gracefully on 401/403.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json
from app.services.providers.types import normalize_reputation


class ShodanProvider(BaseProvider):
    name = "shodan"
    kind = "ip"
    enabled = True
    requires_key = True
    api_key_env = "SHODAN_API_KEY"
    rate_limit_per_minute = 10  # free tier
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 10.0
    health_url = "https://api.shodan.io/api-info"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        data = await get_json(
            f"https://api.shodan.io/shodan/host/{target}",
            params={"key": self.api_key or ""},
        )
        if not data or not isinstance(data, dict) or data.get("error"):
            return {
                "found": False,
                "ip": target,
                "ports": [],
                "vulns": [],
                "score": 0,
                "threat_level": "unknown",
                "extra": data if isinstance(data, dict) else {"error": "no data"},
            }

        ports = data.get("ports") or []
        vulns = list((data.get("vulns") or {}).keys())

        # Risk heuristic: open ports + known vulns
        risk_score = min(100, len(ports) * 3 + len(vulns) * 15)
        rep = normalize_reputation(
            malicious=len(vulns),
            suspicious=len(ports),
            score=risk_score,
            extra={
                "org": data.get("org"),
                "asn": data.get("asn"),
                "isp": data.get("isp"),
                "os": data.get("os"),
                "city": data.get("city"),
                "country": data.get("country_name"),
                "hostnames": data.get("hostnames", []),
                "last_update": data.get("last_update"),
            },
        )
        return {
            "found": True,
            "ip": target,
            "ports": ports,
            "vulns": vulns,
            "services_count": len(ports),
            "score": rep["score"],
            "threat_level": rep["threat_level"],
            "extra": rep.get("extra", {}),
        }


PROVIDER_CLASS = ShodanProvider
