"""Settings router (preferences, data export, account deletion)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.core.deps import CurrentUser, get_db
from app.models.investigation import Investigation
from app.models.report import Report
from app.models.user import User
from app.services.exporter import to_json

router = APIRouter(prefix="/settings", tags=["settings"])


class Preferences(BaseModel):
    dark_mode: bool = True
    notifications: bool = True
    email_alerts: bool = False


@router.get("/preferences", response_model=Preferences)
async def get_prefs(user: CurrentUser):
    # We persist nothing in the user model for this educational build, so we
    # return defaults. The frontend can store these in localStorage.
    return Preferences()


@router.put("/preferences", response_model=Preferences)
async def update_prefs(payload: Preferences, user: CurrentUser):
    return payload


@router.get("/export")
async def export_account(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    from sqlalchemy import select
    invs = (await db.execute(
        select(Investigation).where(Investigation.user_id == user.id)
    )).scalars().all()
    blob = {
        "user": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "investigations": [
            {
                "id": i.id, "kind": i.kind, "target": i.target, "title": i.title,
                "risk_score": i.risk_score, "threat_level": i.threat_level,
                "result": i.result, "created_at": i.created_at.isoformat() if i.created_at else None,
            } for i in invs
        ],
    }
    return {
        "filename": "osint-nexus-account-export.json",
        "data": blob,
    }


@router.delete("/account")
async def delete_account(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    await db.execute(delete(Report).where(Report.user_id == user.id))
    await db.execute(delete(Investigation).where(Investigation.user_id == user.id))
    await db.delete(user)
    return {"deleted": True}


@router.get("/info")
async def info():
    """Public, anonymous-friendly: app name/version and OSINT provider status."""
    return {
        "app": app_settings.app_name,
        "providers": {
            "hibp": bool(app_settings.hibp_api_key),
            "abuseipdb": bool(app_settings.abuseipdb_api_key),
            "virustotal": bool(app_settings.virustotal_api_key),
            "supabase_auth": app_settings.use_supabase,
        },
    }
