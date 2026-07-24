"""
AbuseIPDB provider.

Reference: https://docs.abuseipdb.com/

Free tier: 1,000 checks/day, 1 req/sec. The `/check` endpoint returns
the `abuseConfidenceScore` (0-100) and total report count.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json
from app.services.providers.types import normalize_reputation


class AbuseIPDBProvider(BaseProvider):
    name = "abuseipdb"
    kind = "ip"
    enabled = True
    requires_key = True
    api_key_env = "ABUSEIPDB_API_KEY"
    rate_limit_per_minute = 30
    cache_ttl = 60 * 60 * 12
    timeout_seconds = 10.0
    health_url = "https://docs.abuseipdb.com/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        data = await get_json(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": target, "maxAgeInDays": 90, "verbose": ""},
            headers={"Key": self.api_key or "", "Accept": "application/json"},
        )
        if not data or not isinstance(data, dict):
            return {
                "found": False,
                "ip": target,
                "score": 0,
                "threat_level": "unknown",
                "extra": {"reason": "no data"},
            }

        d = (data.get("data") or {})
        abuse_score = int(d.get("abuseConfidenceScore", 0) or 0)
        total_reports = int(d.get("totalReports", 0) or 0)
        distinct_users = int(d.get("numDistinctUsers", 0) or 0)
        last_reported = d.get("lastReportedAt")
        usage = d.get("usageType")
        isp = d.get("isp")
        country = d.get("countryCode")
        is_tor = bool(d.get("isTor"))

        # Map AbuseIPDB's 0..100 to our threat level
        if abuse_score >= 75:
            threat = "critical"
        elif abuse_score >= 50:
            threat = "high"
        elif abuse_score >= 25:
            threat = "medium"
        else:
            threat = "low"

        rep = normalize_reputation(
            malicious=total_reports,
            suspicious=distinct_users,
            score=abuse_score,
            threat_level=threat,  # type: ignore[arg-type]
            extra={
                "abuse_confidence": abuse_score,
                "isp": isp,
                "usage_type": usage,
                "country": country,
                "is_tor": is_tor,
                "last_reported": last_reported,
                "distinct_users": distinct_users,
            },
        )
        return {
            "found": total_reports > 0,
            "ip": target,
            "score": rep["score"],
            "threat_level": rep["threat_level"],
            "total_reports": total_reports,
            "abuse_confidence": abuse_score,
            "is_tor": is_tor,
            "extra": rep.get("extra", {}),
        }


PROVIDER_CLASS = AbuseIPDBProvider
