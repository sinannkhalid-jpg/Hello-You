"""Phone lookup router.

Hardened: any failure inside the provider is caught and the endpoint
returns a 200 with an empty result instead of 500.

The new provider collects:
  • libphonenumber metadata (country, region, carrier, timezone,
    number type, validity, formats)
  • Telegram public link (async)
  • WhatsApp / Signal presence (reported as 'no_public_api' since
    neither platform exposes a public lookup API)
  • Reputation scores (reported as 'no_data' since no public
    reputation source is configured by default)
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.core.logging import get_logger
from app.osint.phone_provider import async_enrichment, lookup as phone_lookup
from app.schemas.osint import PhoneResult
from app.services.investigation_service import save_investigation

router = APIRouter(prefix="/phone", tags=["phone"])
log = get_logger(__name__)


@router.get("/{number}", response_model=PhoneResult)
async def investigate_phone(
    number: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    t0 = time.perf_counter()
    try:
        data = phone_lookup(number)
    except Exception as e:  # noqa: BLE001
        log.warning("phone lookup failed for %r: %s", number, e)
        data = {
            "number": number,
            "e164": number if number and number.startswith("+") else "",
            "valid": False,
            "reason": "lookup_failed",
        }
    # Normalize: e164 must be a non-null string for the schema
    if data.get("e164") is None:
        data["e164"] = ""

    # Run the async enrichment (Telegram public link, etc.)
    try:
        data = await async_enrichment(data)
    except Exception as e:  # noqa: BLE001
        log.debug("phone async_enrichment failed: %s", e)

    duration_ms = int((time.perf_counter() - t0) * 1000)
    await save_investigation(
        db, user.id, kind="phone", target=number, result=data,
        duration_ms=duration_ms,
    )
    return PhoneResult(**data)
