"""
Username investigation router.

Delegates to the new `UsernameProvider` (services.providers.username) but
keeps the legacy response shape (UsernameResult) so the frontend and
existing API consumers do not break.

Response shape (extended):
  - profiles        : list of confirmed matches (found=True)
  - blocked         : list of platforms that could not be checked
                      (rate-limited, Cloudflare, reCAPTCHA, no API)
  - not_found       : list of platforms that returned a clean "not found"
  - count           : number of profiles
  - confidence      : aggregate confidence across profiles
  - total_checked   : total platforms queried
  - providers_blocked : number of platforms that could not be queried
"""
from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.schemas.osint import UsernameResult
from app.services.investigation_service import save_investigation
from app.services.orchestrator import get_orchestrator

router = APIRouter(prefix="/username", tags=["username"])


def _profile_card(r: dict, username: str) -> dict[str, Any]:
    """Map the new provider result shape into the legacy
    `UsernameProfile` shape the frontend expects."""
    return {
        "platform": r.get("platform"),
        "url": r.get("profile_url"),
        "exists": bool(r.get("found")),
        "username": username,
        "display_name": r.get("display_name"),
        "bio": r.get("bio"),
        "avatar_url": r.get("avatar_url"),
        "website": None,
        "followers": (r.get("extra") or {}).get("followers")
                     or (r.get("extra") or {}).get("follower_count"),
        "verified": bool(r.get("verified")),
        "confidence": float(r.get("confidence") or 0.0),
        "response_time_ms": int(r.get("response_time_ms") or 0),
    }


def _blocked_card(r: dict) -> dict[str, Any]:
    return {
        "platform": r.get("platform"),
        "url": r.get("profile_url"),
        "status": "blocked",
        "reason": r.get("block_reason") or "unknown",
        "detail": r.get("block_detail"),
        "response_time_ms": int(r.get("response_time_ms") or 0),
    }


@router.get("/{username}", response_model=UsernameResult)
async def investigate_username(
    username: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not username or len(username) > 64:
        return UsernameResult(
            username=username, profiles=[], confidence=0.0,
            blocked=[], not_found=[], providers_blocked=0,
            total_checked=0, count=0,
        )

    t0 = time.perf_counter()
    orch = get_orchestrator()
    provider = orch.providers.get("username")
    if provider is None:
        # Orchestrator did not register it (shouldn't happen); fall back empty
        result: dict = {"username": username, "count": 0, "confidence": 0.0,
                        "results": [], "blocked": [], "not_found": [],
                        "total_checked": 0}
    else:
        pr = await provider.run(username)
        if pr.ok:
            result = pr.data
        else:
            result = {"username": username, "count": 0, "confidence": 0.0,
                      "results": [], "blocked": [], "not_found": [],
                      "total_checked": 0, "error": pr.error}

    raw_results = result.get("results", []) or []
    raw_blocked = result.get("blocked", []) or []
    raw_not_found = result.get("not_found", []) or []

    profiles = [_profile_card(r, result.get("username") or username) for r in raw_results]
    blocked = [_blocked_card(r) for r in raw_blocked]
    not_found = [{"platform": r.get("platform"), "url": r.get("profile_url"),
                  "confidence": r.get("confidence")}
                 for r in raw_not_found]

    timeline = [{"platform": p["platform"], "url": p["url"], "detected": True} for p in profiles]
    confidence = float(result.get("confidence") or 0.0)
    duration_ms = int((time.perf_counter() - t0) * 1000)

    payload = {
        "username": username,
        "profiles": profiles,
        "blocked": blocked,
        "not_found": not_found,
        "count": len(profiles),
        "providers_blocked": len(blocked),
        "total_checked": int(result.get("total_checked", 0) or 0),
        "confidence": confidence,
        "timeline": timeline,
        "risk_score": 0,
    }
    await save_investigation(
        db, user.id, kind="username", target=username, result=payload,
        duration_ms=duration_ms,
    )
    return UsernameResult(**payload)
