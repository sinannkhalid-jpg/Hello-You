"""Persistence + business logic for investigations."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation
from app.osint.risk import level


async def save_investigation(
    db: AsyncSession,
    user_id: str,
    *,
    kind: str,
    target: str,
    result: dict[str, Any],
    risk_score: int | None = None,
    title: str | None = None,
    duration_ms: int | None = None,
    notes: str | None = None,
) -> Investigation:
    inv = Investigation(
        user_id=user_id,
        kind=kind,
        target=target,
        result=result,
        risk_score=risk_score,
        threat_level=level(risk_score or 0) if risk_score is not None else None,
        title=title or f"{kind.title()}: {target}",
        duration_ms=duration_ms,
        notes=notes,
    )
    db.add(inv)
    await db.flush()
    return inv


async def list_investigations(
    db: AsyncSession,
    user_id: str,
    *,
    kind: str | None = None,
    favorite: bool | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Investigation], int]:
    stmt = select(Investigation).where(Investigation.user_id == user_id)
    count_stmt = select(func.count(Investigation.id)).where(Investigation.user_id == user_id)
    if kind:
        stmt = stmt.where(Investigation.kind == kind)
        count_stmt = count_stmt.where(Investigation.kind == kind)
    if favorite is not None:
        stmt = stmt.where(Investigation.is_favorite == favorite)
        count_stmt = count_stmt.where(Investigation.is_favorite == favorite)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(func.lower(Investigation.target).like(like))
        count_stmt = count_stmt.where(func.lower(Investigation.target).like(like))
    stmt = stmt.order_by(desc(Investigation.created_at)).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar_one()
    return list(rows), int(total)


async def get_investigation(db: AsyncSession, user_id: str, inv_id: str) -> Investigation | None:
    res = await db.execute(
        select(Investigation).where(
            and_(Investigation.id == inv_id, Investigation.user_id == user_id)
        )
    )
    return res.scalar_one_or_none()


async def delete_investigation(db: AsyncSession, user_id: str, inv_id: str) -> bool:
    inv = await get_investigation(db, user_id, inv_id)
    if not inv:
        return False
    await db.delete(inv)
    await db.flush()
    return True


async def toggle_favorite(db: AsyncSession, user_id: str, inv_id: str) -> Investigation | None:
    inv = await get_investigation(db, user_id, inv_id)
    if not inv:
        return None
    inv.is_favorite = not inv.is_favorite
    await db.flush()
    return inv


def to_summary(inv: Investigation) -> dict[str, Any]:
    return {
        "id": inv.id,
        "kind": inv.kind,
        "target": inv.target,
        "title": inv.title,
        "risk_score": inv.risk_score,
        "threat_level": inv.threat_level,
        "is_favorite": inv.is_favorite,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }
