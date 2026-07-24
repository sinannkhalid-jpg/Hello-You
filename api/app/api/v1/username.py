"""
Username investigation router.

Delegates to the new `UsernameProvider` (services.providers.username) but
keeps the legacy response shape (UsernameResult) so the frontend and
existing API consumers do not break.
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.schemas.osint import UsernameResult
from app.services.investigation_service import save_investigation
from app.services.orchestrator import get_orchestrator

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
    orch = get_orchestrator()
    provider = orch.providers.get("username")
    result: dict = {}
    if provider is None:
        # Orchestrator did not register it (shouldn't happen); fall back empty
        result = {"username": username, "count": 0, "confidence": 0.0, "results": []}
    else:
        pr = await provider.run(username)
        result = pr.data if pr.ok else {"username": username, "count": 0, "confidence": 0.0, "results": [], "error": pr.error}

    # Map the new provider shape → legacy `UsernameResult` shape
    raw_results = result.get("results", []) or []
    profiles: list[dict] = []
    for r in raw_results:
        profiles.append(
            {
                "platform": r.get("platform"),
                "url": r.get("profile_url"),
                "exists": bool(r.get("found")),
                "username": result.get("username") or username,
                "display_name": r.get("display_name"),
                "bio": r.get("bio"),
                "avatar_url": r.get("avatar_url"),
                "website": None,
                "followers": None,
                "verified": bool(r.get("verified")),
                "confidence": float(r.get("confidence") or 0.0),
                "response_time_ms": int(r.get("response_time_ms") or 0),
            }
        )

    timeline = [{"platform": p["platform"], "url": p["url"], "detected": True} for p in profiles]
    confidence = float(result.get("confidence") or 0.0)

    duration_ms = int((time.perf_counter() - t0) * 1000)
    payload = {
        "username": username,
        "profiles": profiles,
        "confidence": confidence,
        "timeline": timeline,
        "risk_score": 0,
    }
    await save_investigation(
        db, user.id, kind="username", target=username, result=payload, duration_ms=duration_ms
    )
    return UsernameResult(**payload)
