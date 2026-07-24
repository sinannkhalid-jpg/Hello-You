"""
Email investigation router.

Behavior:
  • DNS / SPF / DKIM / DMARC / Gravatar / HIBP are computed using the
    legacy `app.osint.email_provider` (rich, public-only checks).
  • LeakCheck breach intelligence is added via the new provider
    architecture, **without** changing the legacy response shape.

The result is stored with a `providers` sub-dict so that consumers can
inspect the new aggregated view while the rest of the response remains
backward compatible.
"""
from __future__ import annotations

import time
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.email_provider import (
    dmarc_record,
    dkim_record,
    gravatar_exists,
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


@router.get("/{email}", response_model=EmailResult)
async def investigate_email(
    email: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        v = validate_email(email, check_deliverability=False)
        email = v.normalized
    except EmailNotValidError as e:
        raise HTTPException(400, f"Invalid email: {e}")

    local, domain = split_email(email)
    t0 = time.perf_counter()

    # ---- legacy public signals ---- #
    mx = lookup_mx(domain)
    spf = spf_record(domain)
    dkim = dkim_record(domain)
    dmarc = dmarc_record(domain)
    g_url = gravatar_url(email)
    g_exists = gravatar_exists(email)
    breaches = await hibp_breaches(email)
    score = risk_score(email, mx, spf, dkim, dmarc, breaches, g_exists)

    # ---- new: LeakCheck via orchestrator (optional, non-breaking) ---- #
    providers_data: dict = {}
    orch = get_orchestrator()
    leak = orch.providers.get("leakcheck")
    if leak is not None and leak.enabled:
        pr = await leak.run(email)
        providers_data["leakcheck"] = to_jsonable(pr.to_dict())
        if pr.ok:
            d = pr.data or {}
            if d.get("found") and not breaches:
                # Surface as breach_exposure for the legacy UI
                breaches = {"sources": d.get("sources", []), "via": "leakcheck"}
            if d.get("found"):
                score = max(score, int(d.get("score", 0) or 0))

    score = min(score, 100)
    duration_ms = int((time.perf_counter() - t0) * 1000)

    result = {
        "email": email,
        "domain": domain,
        "mx_records": mx,
        "spf": spf,
        "dkim": dkim,
        "dmarc": dmarc,
        "gravatar_url": g_url if g_exists else None,
        "breach_exposure": breaches,
        "risk_score": score,
        "threat_level": level(score),
        "providers": providers_data,  # new: orchestrator output (non-breaking, stored only)
    }
    await save_investigation(
        db, user.id, kind="email", target=email, result=result,
        risk_score=score, duration_ms=duration_ms,
    )
    # Return only the legacy fields; the new `providers` view is available
    # through /api/v1/intel/investigate or in the saved investigation JSON.
    return EmailResult(
        email=result["email"],
        domain=result["domain"],
        mx_records=result["mx_records"],
        spf=result["spf"],
        dkim=result["dkim"],
        dmarc=result["dmarc"],
        gravatar_url=result["gravatar_url"],
        breach_exposure=result["breach_exposure"],
        risk_score=result["risk_score"],
        threat_level=result["threat_level"],
    )
