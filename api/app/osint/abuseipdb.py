"""AbuseIPDB (optional). Only used if ABUSEIPDB_API_KEY is provided.

Free tier: 1,000 checks/day. https://docs.abuseipdb.com/
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.osint.http import get_json


async def lookup_ip(ip: str, max_age_days: int = 90) -> dict[str, Any] | None:
    if not settings.abuseipdb_api_key:
        return None
    return await get_json(
        "https://api.abuseipdb.com/api/v2/check",
        params={"ipAddress": ip, "maxAgeInDays": max_age_days},
        headers={"Key": settings.abuseipdb_api_key, "Accept": "application/json"},
    )
