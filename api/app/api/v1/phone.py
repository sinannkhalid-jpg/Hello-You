"""Phone lookup router."""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.phone_provider import lookup as phone_lookup
from app.schemas.osint import PhoneResult
from app.services.investigation_service import save_investigation

router = APIRouter(prefix="/phone", tags=["phone"])


@router.get("/{number}", response_model=PhoneResult)
async def investigate_phone(
    number: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    t0 = time.perf_counter()
    data = phone_lookup(number)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    await save_investigation(
        db, user.id, kind="phone", target=number, result=data,
        duration_ms=duration_ms,
    )
    return PhoneResult(**data)
