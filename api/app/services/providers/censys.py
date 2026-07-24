"""
Censys provider (https://search.censys.io/api/v1).

Authentication: HTTP Basic with API_ID + API_SECRET.
"""
from __future__ import annotations

import base64
from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


class CensysProvider(BaseProvider):
    name = "censys"
    kind = "ip"
    enabled = True
    requires_key = True
    api_id_env = "CENSYS_API_ID"
    api_secret_env = "CENSYS_API_SECRET"
    rate_limit_per_minute = 30
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 10.0
    health_url = "https://search.censys.io/api/v1/account"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        # We expect api_key to be set as "id:secret" by the orchestrator
        if not self.api_key or ":" not in (self.api_key or ""):
            return {
                "found": False,
                "ip": target,
                "extra": {"reason": "censys requires CENSYS_API_ID + CENSYS_API_SECRET"},
            }
        api_id, api_secret = self.api_key.split(":", 1)
        token = base64.b64encode(f"{api_id}:{api_secret}".encode()).decode()

        data = await get_json(
            f"https://search.censys.io/api/v1/view/ipv4/{target}",
            headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
        )
        if not data or not isinstance(data, dict):
            return {
                "found": False,
                "ip": target,
                "extra": {"reason": "no data"},
            }

        ports: list[int] = []
        for p in data.get("ports", []) or []:
            if isinstance(p, dict) and isinstance(p.get("port"), int):
                ports.append(p["port"])
            elif isinstance(p, int):
                ports.append(p)

        as_data = data.get("autonomous_system") or {}
        loc = data.get("location") or {}

        return {
            "found": True,
            "ip": target,
            "asn": as_data.get("asn"),
            "asn_org": as_data.get("name") or as_data.get("description"),
            "country": loc.get("country"),
            "city": loc.get("city"),
            "ports": ports,
            "operating_system": data.get("operating_system"),
            "services_count": len(ports),
            "extra": {
                "protocols": data.get("protocols"),
                "asn_country": as_data.get("country"),
            },
        }


PROVIDER_CLASS = CensysProvider
