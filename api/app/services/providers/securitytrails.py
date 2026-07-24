"""
SecurityTrails provider.

Reference: https://docs.securitytrails.com/

Authentication: `APIKEY` header. Provides:
  • current DNS records for a domain
  • historical DNS
  • WHOIS
  • subdomains list
  • associated IPs

We implement the `subdomains` and `domain/{domain}` endpoints.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


class SecurityTrailsProvider(BaseProvider):
    name = "securitytrails"
    kind = "domain"
    enabled = True
    requires_key = True
    api_key_env = "SECURITYTRAILS_API_KEY"
    rate_limit_per_minute = 30  # public tier
    cache_ttl = 60 * 60 * 12
    timeout_seconds = 10.0
    health_url = "https://securitytrails.com/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"APIKEY": self.api_key or "", "Accept": "application/json"}
        base = f"https://api.securitytrails.com/v1/domain/{target}"

        # Run the two most useful endpoints in parallel
        sub_data = await get_json(f"{base}/subdomains", params={"children_only": "false"}, headers=headers)
        whois_data = await get_json(f"{base}/whois", headers=headers)

        subdomains: list[str] = []
        if isinstance(subdata := sub_data, dict):
            for s in (subdata.get("subdomains") or []):
                if isinstance(s, str):
                    subdomains.append(f"{s}.{target}")

        whois_extra: dict[str, Any] = {}
        if isinstance(whois := whois_data, dict):
            whois_extra = {
                "registrar": (whois.get("registrar") or {}).get("name") if isinstance(whois.get("registrar"), dict) else whois.get("registrar"),
                "created_date": whois.get("createdDate"),
                "expiration_date": whois.get("expirationDate"),
                "status": whois.get("status"),
                "name_servers": whois.get("nameServers") or [],
            }

        return {
            "subdomains": sorted(set(subdomains)),
            "whois": whois_extra,
            "found": bool(subdomains) or bool(whois_extra),
        }


PROVIDER_CLASS = SecurityTrailsProvider
