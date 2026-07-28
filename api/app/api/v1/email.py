"""
Email investigation router — comprehensive email intelligence.

Hardened: every step is wrapped in try/except so an optional provider
failing (Gravatar, HIBP, GitHub commit search) never aborts the
investigation. The endpoint always returns a 200 with whatever data
could be gathered.

Response shape (canonical fields):
  {
    "email":              "...",
    "domain":             "...",
    "provider":           "Gmail" / "Outlook" / "Custom" / "Disposable",
    "is_free_mail":       bool,
    "is_disposable":      bool,
    "is_role":            bool,
    "mx_records":         [{"priority": int, "host": str}],
    "spf":                "v=spf1 ..." | null,
    "dkim":               {"found": bool, "selector": str, "value": str} | null,
    "dmarc":              "v=dmarc1 ..." | null,
    "mta_sts":            {"enabled": bool, "mode": str, "policy": str} | null,
    "tls":                {"checked": int, "supports_tls": int, "details": [...]},
    "bimi":               "v=bimi1 ..." | null,
    "dnssec":             {"enabled": bool, "reason": str},
    "nameservers":        [...],
    "domain_age":         {"age_days": int, "created_at": str, "registrar": str},
    "gravatar":           {"exists": bool, "url": str, "status": int},
    "gravatar_profile":   {display_name, bio, location, ...} | null,
    "breach_exposure":    {"configured": bool, "found": bool, "count": int, "breaches": [...]},
    "git_leaks":          {"configured": bool, "found": bool, "count": int, "commits": [...]},
    "leakcheck":          {found, score, sources, configured, reason} | null,
    "risk_score":         int,                 # 0-100, higher = higher risk
    "risk_level":         str,                 # "Low Risk" / "Guarded" / "Moderate" / "High Risk" / "Critical"
    "risk":               {score, level, color, findings},  # full breakdown
    "providers":          {name: status dict per provider},
  }

The legacy fields `reputation`, `threat_level`, and a duplicate
`risk_score` (int) are kept for backward compatibility with
existing clients but are deprecated. New clients should read
`risk_score` and `risk_level`.
"""
from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.core.logging import get_logger
from app.core.risk import classify
from app.osint.email_provider import (
    bimi_record, classify_provider, dkim_record, dmarc_record,
    dnssec_status, domain_age, git_leaks, gravatar_exists,
    gravatar_profile, hibp_breaches, mta_sts_record, nameservers,
    risk_score_for_email, spf_record, split_email, tls_capability,
)
from app.osint.dns_provider import lookup_mx
from app.schemas.osint import EmailResult
from app.services.investigation_service import save_investigation
from app.services.orchestrator import get_orchestrator
from app.services.serializer import to_jsonable

router = APIRouter(prefix="/email", tags=["email"])
log = get_logger("email")


def _safe(fn, *args, **kwargs):
    """Sync try/except wrapper."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        log.debug("safe(%s) error: %s", getattr(fn, "__name__", fn), e)
        return None


async def _safe_async(coro):
    try:
        return await coro
    except Exception as e:  # noqa: BLE001
        log.debug("safe_async error: %s", e)
        return None


async def _safe_leakcheck(email: str) -> dict | None:
    """Return a small summary dict if LeakCheck is enabled, else None."""
    try:
        orch = get_orchestrator()
        lc = orch.providers.get("leakcheck")
        if lc is None or not lc.enabled:
            return {
                "configured": False,
                "reason": "no_api_key",
                "key_env": "LEAKCHECK_API_KEY",
            }
        r = await lc.run(email)
        if not r.ok:
            return {
                "configured": True,
                "found": None,
                "reason": r.error or "lookup_failed",
            }
        d = r.data or {}
        return {
            "configured": True,
            "found": bool(d.get("found")),
            "score": int(d.get("score", 0) or 0),
            "sources": (d.get("sources") or [])[:5],
            "reason": None,
        }
    except Exception:  # noqa: BLE001
        return None


@router.get("/{email}", response_model=EmailResult)
async def investigate_email(
    email: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # 1. Validate
    try:
        v = validate_email(email, check_deliverability=False)
        email = v.normalized
    except EmailNotValidError as e:
        raise HTTPException(400, f"Invalid email: {e}")

    # 2. Parse
    try:
        _local, domain = split_email(email)
    except ValueError as e:
        raise HTTPException(400, f"Invalid email: {e}")

    t0 = time.perf_counter()

    # 3. Provider diagnostics — track each provider's status.
    provider_diagnostics: dict[str, dict[str, Any]] = {}

    # 3a. Sync DNS-backed signals (all wrapped in try/except)
    mx_raw = _safe(lookup_mx, domain) or []
    provider_diagnostics["mx"] = {
        "status": "ok" if mx_raw else "no_records",
        "count": len(mx_raw),
        "records": mx_raw,
    }
    spf = _safe(spf_record, domain)
    provider_diagnostics["spf"] = {
        "status": "ok" if spf else "no_record",
        "value": spf,
    }
    dkim = _safe(dkim_record, domain) or {"found": False, "selector": None, "value": None}
    provider_diagnostics["dkim"] = {
        "status": "ok" if dkim.get("found") else "no_record",
        "selector": dkim.get("selector"),
        "value": dkim.get("value"),
    }
    dmarc = _safe(dmarc_record, domain)
    provider_diagnostics["dmarc"] = {
        "status": "ok" if dmarc else "no_record",
        "value": dmarc,
    }
    bimi = _safe(bimi_record, domain)
    provider_diagnostics["bimi"] = {
        "status": "ok" if bimi else "no_record",
        "value": bimi,
    }
    mta_sts = _safe(mta_sts_record, domain) or {"enabled": None, "policy": None, "mode": None}
    provider_diagnostics["mta_sts"] = {
        "status": "ok" if mta_sts.get("enabled") else
                  "disabled" if mta_sts.get("enabled") is False else
                  "lookup_failed",
        "enabled": mta_sts.get("enabled"),
        "mode": mta_sts.get("mode"),
    }
    dnssec = _safe(dnssec_status, domain) or {"enabled": None, "reason": "lookup_failed"}
    provider_diagnostics["dnssec"] = {
        "status": "enabled" if dnssec.get("enabled") else
                  "disabled" if dnssec.get("enabled") is False else
                  "lookup_failed",
        "enabled": dnssec.get("enabled"),
    }
    ns = _safe(nameservers, domain) or []
    provider_diagnostics["nameservers"] = {
        "status": "ok" if ns else "no_records",
        "records": ns,
    }

    classification = classify_provider(domain)
    is_disposable = bool(classification.get("is_disposable"))

    # 3b. Async probes — each in its own try/except so any one failure
    #     is silently absorbed and reported as "no data".
    mx_hosts = [m.get("host", "") for m in mx_raw if m.get("host")]

    gravatar_data, hibp_data, gravatar_prof, git_leaks_data, leakcheck_intel, tls_data = await asyncio.gather(
        _safe_async(gravatar_exists(email)),
        _safe_async(hibp_breaches(email)),
        _safe_async(gravatar_profile(email)),
        _safe_async(git_leaks(email)),
        _safe_leakcheck(email),
        _safe_async(tls_capability(mx_hosts)),
        return_exceptions=False,
    )

    gravatar_data = gravatar_data or {"exists": None, "url": None, "status": None, "reason": "no_data"}
    hibp_data = hibp_data or {"configured": False, "found": None, "count": 0,
                              "breaches": [], "reason": "no_data"}
    git_leaks_data = git_leaks_data or {"configured": True, "found": None, "count": 0,
                                        "commits": [], "reason": "no_data"}
    leakcheck_intel = leakcheck_intel or {"configured": False, "reason": "no_data"}
    tls_data = tls_data or {"checked": 0, "supports_tls": 0, "details": [],
                            "reason": "no_data"}

    # Provider diagnostics for the async probes
    provider_diagnostics["gravatar"] = {
        "status": "configured" if gravatar_data.get("exists") else
                  "not_configured" if gravatar_data.get("exists") is False else
                  "lookup_failed",
        "url": gravatar_data.get("url"),
        "status_code": gravatar_data.get("status"),
    }
    provider_diagnostics["hibp"] = {
        "status": "no_api_key" if not hibp_data.get("configured") else
                  "ok" if hibp_data.get("found") is not None else
                  "blocked",
        "configured": hibp_data.get("configured"),
        "reason": hibp_data.get("reason"),
        "breach_count": hibp_data.get("count", 0),
    }
    provider_diagnostics["leakcheck"] = {
        "status": "no_api_key" if not leakcheck_intel.get("configured") else
                  "ok" if leakcheck_intel.get("found") is not None else
                  "blocked",
        "configured": leakcheck_intel.get("configured"),
        "reason": leakcheck_intel.get("reason"),
    }
    provider_diagnostics["git_leaks"] = {
        "status": "ok" if git_leaks_data.get("found") else
                  "no_commits" if git_leaks_data.get("found") is False else
                  "blocked",
        "configured": git_leaks_data.get("configured"),
        "reason": git_leaks_data.get("reason"),
        "commit_count": git_leaks_data.get("count", 0),
    }
    provider_diagnostics["tls"] = {
        "status": "ok" if tls_data.get("supports_tls", 0) > 0 else
                  "not_supported" if tls_data.get("checked", 0) > 0 else
                  "not_checked",
        "checked": tls_data.get("checked", 0),
        "supports_tls": tls_data.get("supports_tls", 0),
    }

    # Domain age via RDAP
    domain_age_data = await _safe_async(domain_age(domain)) or \
        {"age_days": None, "registrar": None, "reason": "lookup_failed"}
    provider_diagnostics["rdap"] = {
        "status": "ok" if domain_age_data.get("age_days") is not None else "lookup_failed",
        "registrar": domain_age_data.get("registrar"),
        "age_days": domain_age_data.get("age_days"),
    }

    # 4. Compose breach_exposure
    breach_count = 0
    breach_list: list[dict] = []
    if hibp_data.get("found"):
        breach_count = int(hibp_data.get("count") or 0)
        breach_list = (hibp_data.get("breaches") or [])[:5]
    elif leakcheck_intel.get("found") and isinstance(leakcheck_intel.get("sources"), list):
        breach_count = len(leakcheck_intel["sources"])
        breach_list = leakcheck_intel["sources"]

    # 5. Risk score (canonical, 0-100, higher = higher risk)
    risk = risk_score_for_email(
        mx=mx_raw, spf=spf, dkim=dkim, dmarc=dmarc,
        mta_sts=mta_sts, tls=tls_data, dnssec=dnssec,
        gravatar=gravatar_data, breach=hibp_data, git_leaks=git_leaks_data,
        classification=classification,
        domain_age=domain_age_data,
    )

    # Defense-in-depth: if classify() somehow missed it, classify again.
    cls = classify(risk["risk_score"])

    duration_ms = int((time.perf_counter() - t0) * 1000)

    result = {
        "email": email,
        "domain": domain,
        "provider": classification.get("provider"),
        "is_free_mail": bool(classification.get("is_free_mail")),
        "is_disposable": is_disposable,
        "is_role": bool(classification.get("is_role")),
        "mx_records": mx_raw,
        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,
        "mta_sts": mta_sts,
        "tls": tls_data,
        "bimi": bimi,
        "dnssec": dnssec,
        "nameservers": ns,
        "domain_age": domain_age_data,
        "gravatar_url": gravatar_data.get("url"),
        "gravatar_profile": gravatar_prof,
        "breach_exposure": {
            "configured": hibp_data.get("configured", False),
            "found": bool(breach_count > 0),
            "count": breach_count,
            "samples": breach_list,
            "reason": hibp_data.get("reason"),
        },
        "git_leaks": {
            "configured": git_leaks_data.get("configured", True),
            "found": bool(git_leaks_data.get("count", 0) > 0),
            "count": int(git_leaks_data.get("count", 0) or 0),
            "commits": git_leaks_data.get("commits", []),
            "reason": git_leaks_data.get("reason"),
        },
        "leakcheck": leakcheck_intel,
        # Canonical risk fields (new)
        "risk_score": cls["risk_score"],
        "risk_level": cls["risk_level"],
        "risk": {
            "score": cls["risk_score"],
            "level": cls["risk_level"],
            "color": cls["color"],
            "findings": risk.get("findings", []),
        },
        # Back-compat: legacy aliases
        "reputation": {
            "score": cls["risk_score"],
            "threat_level": _legacy_token(cls["risk_level"]),
            "findings": risk.get("findings", []),
        },
        "threat_level": _legacy_token(cls["risk_level"]),
        "providers": provider_diagnostics,
        "duration_ms": duration_ms,
    }
    await save_investigation(
        db, user.id, kind="email", target=email, result=to_jsonable(result),
        risk_score=cls["risk_score"], duration_ms=duration_ms,
    )
    return EmailResult(**result)


def _legacy_token(name: str) -> str:
    """Convert canonical name to short token for legacy fields."""
    return {
        "Low Risk":  "low",
        "Guarded":   "guarded",
        "Moderate":  "medium",
        "High Risk": "high",
        "Critical":  "critical",
    }.get(name, "medium")
