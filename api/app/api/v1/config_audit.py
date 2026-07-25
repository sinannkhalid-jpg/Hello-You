"""
API configuration audit endpoint.

Exposes a single endpoint that audits every external API the platform
can use, reporting for each:
  • Configured: Yes / No
  • Reason:      "Missing environment variable" / "Found" / etc.
  • Required variable(s)
  • Provider status (Online / Offline / Disabled / Blocked)

This is what the user asked for in section 8 of the requirements:
  "If an API key is missing return:
   Configured: No
   Reason: Missing environment variable
   Required variable: HIBP_API_KEY"
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser
from app.services.orchestrator import get_orchestrator

router = APIRouter(prefix="/config", tags=["config"])


# All APIs the platform can use, with the env var(s) they need.
# Updated to reflect the actual provider set: Censys, SecurityTrails,
# VirusTotal, Hunter, IPInfo, AbuseIPDB, Shodan, HIBP, EmailRep,
# Gravatar, LeakCheck, IPQualityScore, Numverify, etc.
API_AUDIT: list[dict[str, Any]] = [
    {
        "name": "Censys",
        "purpose": "IP & domain certificate search (Platform API v3)",
        "env_vars": ["CENSYS_PAT"],
        "legacy_env_vars": ["CENSYS_API_ID", "CENSYS_API_SECRET"],
        "kind": "ip",
        "provider": "censys",
        "test_url": "https://api.censys.io/v1/account",
    },
    {
        "name": "SecurityTrails",
        "purpose": "Domain history & passive DNS",
        "env_vars": ["SECURITYTRAILS_API_KEY"],
        "kind": "domain",
        "provider": "securitytrails",
    },
    {
        "name": "VirusTotal",
        "purpose": "File / URL / domain / IP reputation",
        "env_vars": ["VIRUSTOTAL_API_KEY"],
        "kind": "domain",
        "provider": "virustotal",
    },
    {
        "name": "Hunter",
        "purpose": "Email & domain intelligence (Hunter.io)",
        "env_vars": ["HUNTER_API_KEY"],
        "kind": "domain",
        "provider": None,  # not currently a registered provider
        "note": "Not currently wired into the orchestrator; reserved for future use.",
    },
    {
        "name": "IPInfo",
        "purpose": "IP geolocation & ASN",
        "env_vars": ["IPINFO_TOKEN", "IPAPI_KEY"],
        "kind": "ip",
        "provider": "ipapi",
        "note": "Provider name is 'ipapi' but uses IPInfo's free endpoint without a key.",
    },
    {
        "name": "AbuseIPDB",
        "purpose": "IP abuse reports",
        "env_vars": ["ABUSEIPDB_API_KEY"],
        "kind": "ip",
        "provider": "abuseipdb",
    },
    {
        "name": "Shodan",
        "purpose": "Internet-wide scan data",
        "env_vars": ["SHODAN_API_KEY"],
        "kind": "ip",
        "provider": "shodan",
    },
    {
        "name": "Have I Been Pwned",
        "purpose": "Email breach intelligence",
        "env_vars": ["HIBP_API_KEY"],
        "kind": "email",
        "provider": "hibp",
    },
    {
        "name": "EmailRep",
        "purpose": "Email reputation lookup",
        "env_vars": ["EMAILREP_API_KEY"],
        "kind": "email",
        "provider": None,
        "note": "Not currently a registered provider; reserved for future use.",
    },
    {
        "name": "Gravatar",
        "purpose": "Public avatar lookup by email",
        "env_vars": [],  # No key required
        "kind": "email",
        "provider": "gravatar",
        "note": "No API key required.",
    },
    {
        "name": "LeakCheck",
        "purpose": "Aggregated breach lookup",
        "env_vars": ["LEAKCHECK_API_KEY"],
        "kind": "email",
        "provider": "leakcheck",
    },
    {
        "name": "IPQualityScore",
        "purpose": "IP / email / phone fraud score",
        "env_vars": ["IPQUALITYSCORE_API_KEY"],
        "kind": "ip",
        "provider": None,
        "note": "Not currently a registered provider; reserved for future use.",
    },
    {
        "name": "Numverify",
        "purpose": "Phone number validation & carrier lookup",
        "env_vars": ["NUMVERIFY_API_KEY"],
        "kind": "phone",
        "provider": None,
        "note": "Not currently a registered provider; phone lookups use libphonenumber metadata.",
    },
    {
        "name": "IntelX",
        "purpose": "Free-tier public leak search",
        "env_vars": [],  # Free tier with rate limits
        "kind": "domain",
        "provider": "intelx",
        "note": "Free tier; rate-limited but no key required.",
    },
    {
        "name": "crtsh",
        "purpose": "Certificate Transparency log search",
        "env_vars": [],  # No key required
        "kind": "domain",
        "provider": "crtsh",
        "note": "No API key required.",
    },
    {
        "name": "RDAP",
        "purpose": "Domain registration data (whois)",
        "env_vars": [],
        "kind": "domain",
        "provider": None,
        "note": "Public RDAP bootstrap; no key required.",
    },
]


def _status_for_api(api: dict[str, Any], provider_inst: Any) -> dict[str, Any]:
    """Determine the configured/missing/blocked status for an API."""
    env_vars: list[str] = list(api.get("env_vars", []))
    legacy = list(api.get("legacy_env_vars", []))
    all_keys = env_vars + legacy

    if not all_keys:
        # No key required
        configured = True
        reason = "No API key required"
        missing: list[str] = []
    else:
        present = [k for k in all_keys if os.getenv(k)]
        missing = [k for k in all_keys if not os.getenv(k)]
        if present:
            configured = True
            reason = f"Found in {', '.join(present)}"
        else:
            configured = False
            reason = f"Missing environment variable: {missing[0]}"

    # Provider status
    if provider_inst is None and api.get("provider") is not None:
        provider_status = "not_registered"
    elif provider_inst is not None:
        if not provider_inst.enabled:
            if api.get("env_vars"):
                provider_status = "missing_key"
            else:
                provider_status = "disabled"
        else:
            provider_status = "registered"
    else:
        provider_status = "not_registered"

    out = {
        "name": api["name"],
        "purpose": api["purpose"],
        "kind": api.get("kind"),
        "provider": api.get("provider"),
        "required_variables": env_vars,
        "legacy_variables": legacy,
        "missing_variables": missing,
        "configured": configured,
        "reason": reason,
        "provider_status": provider_status,
    }
    if "note" in api:
        out["note"] = api["note"]
    return out


@router.get("/audit")
async def audit(
    user: CurrentUser,
    probe: bool = False,
) -> dict[str, Any]:
    """Audit every external API the platform can use.

    If `probe=true`, also issues a real HTTP probe against each
    provider's health URL (slow; intended for ops dashboards).
    """
    orch = get_orchestrator()
    providers_by_name: dict[str, Any] = {p.name: p for p in orch.providers.values()}

    apis: list[dict[str, Any]] = []
    for api in API_AUDIT:
        provider_inst = providers_by_name.get(api.get("provider", "") or "")
        entry = _status_for_api(api, provider_inst)
        apis.append(entry)

    summary = {
        "total": len(apis),
        "configured": sum(1 for a in apis if a["configured"]),
        "missing_key": sum(1 for a in apis if not a["configured"]),
        "registered": sum(1 for a in apis if a["provider_status"] == "registered"),
        "missing_key_providers": sum(1 for a in apis if a["provider_status"] == "missing_key"),
        "not_registered": sum(1 for a in apis if a["provider_status"] == "not_registered"),
    }

    out: dict[str, Any] = {
        "checked_at": time.time(),
        "summary": summary,
        "apis": apis,
    }

    if probe:
        # Issue real HTTP probes against the providers that have a
        # `health_url` (set on the provider instance)
        async def _probe(provider_inst: Any) -> dict[str, Any] | None:
            if provider_inst is None or not provider_inst.enabled:
                return None
            try:
                res = await provider_inst.healthcheck()
                return {
                    "provider": provider_inst.name,
                    "ok": bool(res.get("ok")),
                    "duration_ms": int(res.get("duration_ms", 0) or 0),
                    "status": "online" if res.get("ok") else "offline",
                    "detail": (res.get("detail") or "")[:200],
                }
            except Exception as e:  # noqa: BLE001
                return {
                    "provider": provider_inst.name,
                    "ok": False,
                    "status": "offline",
                    "detail": str(e)[:200],
                }

        probes = [_probe(p) for p in orch.providers.values()]
        results = await asyncio.gather(*probes, return_exceptions=True)
        out["probes"] = [r for r in results if isinstance(r, dict)]

    return out
