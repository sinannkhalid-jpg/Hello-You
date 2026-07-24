"""
ipapi provider (https://ipapi.co).

Free tier: ~1k req/day without a key. The free tier returns a
JSON document with geolocation, ISP, ASN, timezone, currency, etc.
We support an optional `IPAPI_KEY` (paid tier raises the rate limit).
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


class IPAPIProvider(BaseProvider):
    name = "ipapi"
    kind = "ip"
    enabled = True
    requires_key = False  # free tier works without a key
    api_key_env = "IPAPI_KEY"
    rate_limit_per_minute = 30
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 8.0
    health_url = "https://ipapi.co/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        url = f"https://ipapi.co/{target}/json/"
        data = await get_json(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else None,
        )
        if not data or not isinstance(data, dict) or data.get("error"):
            reason = data.get("error") if isinstance(data, dict) else "no data"
            return {
                "found": False,
                "ip": target,
                "geo": {},
                "isp": None,
                "asn": None,
                "extra": {"reason": reason},
            }

        return {
            "found": True,
            "ip": target,
            "geo": {
                "country": data.get("country_name"),
                "country_code": data.get("country_code"),
                "region": data.get("region"),
                "city": data.get("city"),
                "postal": data.get("postal"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("time_zone") or data.get("timezone"),
            },
            "isp": data.get("org") or data.get("asn"),
            "asn": data.get("asn"),
            "asn_org": data.get("asn_org") or data.get("org"),
            "company": data.get("company") or {},
            "currency": data.get("currency_name"),
            "languages": data.get("languages"),
            "extra": {
                "in_eu": data.get("in_eu"),
                "calling_code": data.get("country_calling_code"),
            },
        }


PROVIDER_CLASS = IPAPIProvider
