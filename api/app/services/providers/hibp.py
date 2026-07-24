"""
Have I Been Pwned (HIBP) provider.

Reference: https://haveibeenpwned.com/API/v3

Authentication: `hibp-api-key` header (paid tier required for the
breachaccount endpoint; the password range API is also gated).

We support two lookups:
  • email   → `breachedaccount/{email}` (returns a list of breaches)
  • domain  → not supported by HIBP — returns empty result

If no key is configured, the provider auto-disables.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json
from app.services.providers.types import normalize_reputation


class HIBPProvider(BaseProvider):
    name = "hibp"
    kind = "email"
    enabled = True
    requires_key = True
    api_key_env = "HIBP_API_KEY"
    rate_limit_per_minute = 10  # HIBP allows 10 req/min on the breach endpoint
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 12.0
    health_url = "https://haveibeenpwned.com/api/v3/breaches"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        if "@" not in target:
            return {
                "found": False,
                "breaches": [],
                "score": 0,
                "threat_level": "unknown",
                "extra": {"reason": "HIBP only supports email addresses"},
            }

        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{target}"
        # truncateResponse=false so we get the full breach list
        data = await get_json(
            url,
            params={"truncateResponse": "false"},
            headers={"hibp-api-key": self.api_key or ""},
        )

        if data is None:
            return {
                "found": False,
                "breaches": [],
                "score": 0,
                "threat_level": "unknown",
                "extra": {"reason": "no response"},
            }
        if isinstance(data, dict) and data.get("statusCode") == 404:
            # Clean — no breaches
            return {
                "found": False,
                "breaches": [],
                "score": 0,
                "threat_level": "low",
                "extra": {"message": "no breaches found"},
            }
        if not isinstance(data, list):
            return {
                "found": False,
                "breaches": [],
                "score": 0,
                "threat_level": "unknown",
                "extra": {"reason": "unexpected response shape"},
            }

        breaches = []
        for b in data:
            breaches.append({
                "name": b.get("Name"),
                "domain": b.get("Domain"),
                "breach_date": b.get("BreachDate"),
                "pwn_count": b.get("PwnCount"),
                "data_classes": b.get("DataClasses", []),
                "description": (b.get("Description") or "")[:200],
            })

        # Heuristic: more breaches = higher risk
        n = len(breaches)
        score = min(100, n * 15)
        rep = normalize_reputation(
            suspicious=n,
            score=score,
            extra={"breach_count": n, "pwn_total": sum((b.get("pwn_count") or 0) for b in breaches)},
        )
        return {
            "found": n > 0,
            "breaches": breaches,
            "score": rep["score"],
            "threat_level": rep["threat_level"],
            "extra": rep.get("extra", {}),
        }


PROVIDER_CLASS = HIBPProvider
