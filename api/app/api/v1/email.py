"""
Email investigation router.

Hardened version: every step is wrapped in try/except so that an
optional provider failing (Gravatar, HIBP) never aborts the whole
investigation. The endpoint always returns a 200 with whatever data
could be gathered.
"""
from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.email_provider import (
    disposable_domain,
    dkim_record,
    dmarc_record,
    gravatar_exists,
    gravatar_profile,
    gravatar_url,
    hibp_breaches,
    risk_score,
    spf_record,
    split_email,
)
from app.osint.dns_provider import lookup_mx
from app.schemas.osint import EmailResult
from app.osint.risk import level
from app.services.investigation_service import save_investigation
from app.services.orchestrator import get_orchestrator
from app.services.serializer import to_jsonable

router = APIRouter(prefix="/email", tags=["email"])


def _level(score: int) -> str:
    """Backwards-compatible wrapper around `level()`."""
    try:
        return level(score)
    except Exception:  # noqa: BLE001
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "medium"
        return "low"


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

    # 3. DNS-backed signals — each is independently try/except'd.
    def _safe(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            from app.core.logging import get_logger
            get_logger("email").debug("safe(%s) error: %s", fn.__name__, e)
            return None

    mx = _safe(lookup_mx, domain) or []
    spf = _safe(spf_record, domain)
    dkim = _safe(dkim_record, domain)
    dmarc = _safe(dmarc_record, domain)
    is_disposable = _safe(disposable_domain, domain) or False

    # 4. Async probes — each in its own try/except so any one failure
    #    is silently absorbed and reported as "no data".
    async def _safe_async(coro):
        try:
            return await coro
        except Exception as e:  # noqa: BLE001
            from app.core.logging import get_logger
            get_logger("email").debug("safe_async error: %s", e)
            return None

    g_exists, breaches, g_profile, leakcheck_intel = await asyncio.gather(
        _safe_async(gravatar_exists(email)),
        _safe_async(hibp_breaches(email)),
        _safe_async(gravatar_profile(email)),
        _safe_leakcheck(email),
        return_exceptions=False,
    )

    # 5. Optional: enrich with LeakCheck via the new provider architecture.
    #    (Already on the orchestrator; we just look it up.)
    try:
        orch = get_orchestrator()
        lc = orch.providers.get("leakcheck")
        if lc is not None and lc.enabled:
            r = await lc.run(email)
            if r.ok:
                d = r.data or {}
                if d.get("found") and not breaches:
                    breaches = {"sources": d.get("sources", []), "via": "leakcheck"}
                if d.get("found"):
                    # The provider score contributes to the final risk
                    lc_score = int(d.get("score", 0) or 0)
                    leakcheck_intel = {"score": lc_score, "sources": d.get("sources", [])[:5]}
    except Exception:  # noqa: BLE001
        pass

    # 6. Compose the canonical response
    g_url = gravatar_url(email)
    gravatar_result_url = g_url if g_exists else None

    # Surface breach count
    breach_count = 0
    breach_list: list[dict] = []
    if isinstance(breaches, list):
        breach_count = len(breaches)
        breach_list = breaches if breach_count <= 5 else breaches[:5]
    elif isinstance(breaches, dict):
        sources = breaches.get("sources") or []
        breach_count = len(sources) if isinstance(sources, list) else 1
        breach_list = sources if isinstance(sources, list) else []

    # 7. Risk score
    score = risk_score(email, mx, spf, dkim, dmarc, breaches, g_exists)
    if leakcheck_intel and leakcheck_intel.get("score"):
        score = max(score, int(leakcheck_intel["score"]))
    score = min(score, 100)

    duration_ms = int((time.perf_counter() - t0) * 1000)

    result = {
        "email": email,
        "domain": domain,
        "mx_records": mx,
        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,
        "gravatar_url": gravatar_result_url,
        "gravatar_profile": g_profile,
        "breach_exposure": {
            "found": breach_count > 0,
            "count": breach_count,
            "samples": breach_list,
        } if breaches else None,
        "disposable": is_disposable,
        "leakcheck": leakcheck_intel,
        "risk_score": score,
        "threat_level": _level(score),
    }
    await save_investigation(
        db, user.id, kind="email", target=email, result=to_jsonable(result),
        risk_score=score, duration_ms=duration_ms,
    )
    return EmailResult(**result)


async def _safe_leakcheck(email: str) -> dict | None:
    """Return a small summary dict if LeakCheck is enabled, else None."""
    try:
        orch = get_orchestrator()
        lc = orch.providers.get("leakcheck")
        if lc is None or not lc.enabled:
            return None
        r = await lc.run(email)
        if not r.ok:
            return None
        d = r.data or {}
        return {
            "found": bool(d.get("found")),
            "score": int(d.get("score", 0) or 0),
            "sources": (d.get("sources") or [])[:5],
        }
    except Exception:  # noqa: BLE001
        return None
