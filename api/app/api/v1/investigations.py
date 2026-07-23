"""Search history / saved investigations router."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.schemas.osint import InvestigationDetail, InvestigationSummary
from app.services.investigation_service import (
    delete_investigation,
    get_investigation,
    list_investigations,
    toggle_favorite,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("", response_model=list[InvestigationSummary])
async def list_my(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    kind: str | None = None,
    favorite: bool | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    rows, _ = await list_investigations(
        db, user.id, kind=kind, favorite=favorite, search=search, limit=limit, offset=offset
    )
    return [InvestigationSummary.model_validate(r) for r in rows]


@router.get("/{inv_id}", response_model=InvestigationDetail)
async def get_one(
    inv_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    inv = await get_investigation(db, user.id, inv_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return InvestigationDetail.model_validate(inv)


@router.post("/{inv_id}/favorite", response_model=InvestigationSummary)
async def favorite(
    inv_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    inv = await toggle_favorite(db, user.id, inv_id)
    if not inv:
        raise HTTPException(404, "Investigation not found")
    return InvestigationSummary.model_validate(inv)


@router.delete("/{inv_id}")
async def delete(inv_id: str, user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    ok = await delete_investigation(db, user.id, inv_id)
    if not ok:
        raise HTTPException(404, "Investigation not found")
    return {"deleted": True}
