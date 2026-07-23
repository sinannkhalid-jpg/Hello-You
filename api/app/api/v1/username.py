"""Username investigation router."""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.username_provider import enumerate_username
from app.schemas.osint import UsernameResult
from app.services.investigation_service import save_investigation

router = APIRouter(prefix="/username", tags=["username"])


@router.get("/{username}", response_model=UsernameResult)
async def investigate_username(
    username: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not username or len(username) > 64:
        return UsernameResult(username=username, profiles=[], confidence=0.0)
    t0 = time.perf_counter()
    profiles = await enumerate_username(username)
    confidence = min(1.0, len(profiles) / 6.0) if profiles else 0.0
    timeline = [
        {"platform": p["platform"], "url": p["url"], "detected": True}
        for p in profiles
    ]
    duration_ms = int((time.perf_counter() - t0) * 1000)
    result = {
        "username": username,
        "profiles": profiles,
        "confidence": confidence,
        "timeline": timeline,
        "risk_score": 0,  # by itself, username reuse is informational
    }
    await save_investigation(
        db, user.id, kind="username", target=username, result=result, duration_ms=duration_ms
    )
    return UsernameResult(**result)
