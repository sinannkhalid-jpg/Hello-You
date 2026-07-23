"""IP intelligence using only free, public, no-key APIs by default.

Primary: ipapi.co (free, ~1k/day, no key).
Fallback: ip-api.com (free, no key, commercial use restricted to <50 req/min).
We never call paid services unless the user supplies a key.
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.osint.http import get_json
from app.osint.dns_provider import lookup_ptr

log = get_logger(__name__)


async def _ipapi_co(ip: str) -> dict[str, Any] | None:
    url = f"{settings.ipapi_base_url.rstrip('/')}/{ip}/json/"
    return await get_json(url)


async def _ip_api_com(ip: str) -> dict[str, Any] | None:
    return await get_json(f"http://ip-api.com/json/{ip}")


async def geolocate(ip: str) -> dict[str, Any]:
    data = await _ipapi_co(ip)
    if not data or data.get("error"):
        data = await _ip_api_com(ip)
    if not data:
        return {"geo": {}, "isp": None, "asn": None, "asn_org": None, "reverse_dns": None}

    geo = {
        "country": data.get("country_name") or data.get("country"),
        "country_code": data.get("country_code") or data.get("countryCode"),
        "region": data.get("region") or data.get("regionName"),
        "city": data.get("city"),
        "latitude": data.get("latitude") or data.get("lat"),
        "longitude": data.get("longitude") or data.get("lon"),
        "timezone": data.get("time_zone") or data.get("timezone"),
    }
    return {
        "geo": geo,
        "isp": data.get("org") or data.get("isp"),
        "asn": data.get("asn"),
        "asn_org": data.get("asn_org") or (data.get("asn") if isinstance(data.get("asn"), str) else None),
        "reverse_dns": (await _reverse_dns(ip)),
    }


async def _reverse_dns(ip: str) -> str | None:
    try:
        import socket
        import asyncio

        host, *_ = await asyncio.get_event_loop().run_in_executor(
            None, lambda: socket.gethostbyaddr(ip)
        )
        return host
    except Exception:
        ptr = lookup_ptr(ip)
        return ptr[0] if ptr else None


async def threat_intel(ip: str) -> dict[str, Any]:
    """Aggregate basic threat signals. Only uses AbuseIPDB if a key is set."""
    out: dict[str, Any] = {"sources": []}
    if settings.abuseipdb_api_key:
        try:
            from app.osint.abuseipdb import lookup_ip  # local import to avoid loading if no key
            r = await lookup_ip(ip)
            if r:
                out["sources"].append("abuseipdb")
                out["abuseipdb"] = r
        except Exception as e:
            log.debug("AbuseIPDB lookup failed: %s", e)
    return out
