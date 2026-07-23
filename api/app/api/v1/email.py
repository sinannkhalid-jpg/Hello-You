"""Email investigation router."""
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
    mx = lookup_mx(domain)
    spf = spf_record(domain)
    dkim = dkim_record(domain)
    dmarc = dmarc_record(domain)
    g_url = gravatar_url(email)
    g_exists = gravatar_exists(email)
    breaches = await hibp_breaches(email)
    score = risk_score(email, mx, spf, dkim, dmarc, breaches, g_exists)
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
    }
    await save_investigation(
        db, user.id, kind="email", target=email, result=result,
        risk_score=score, duration_ms=duration_ms,
    )
    return EmailResult(**result)
