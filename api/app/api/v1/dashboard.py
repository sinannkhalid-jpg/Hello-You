"""Dashboard stats router — recent activity, threat distribution, timeline."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.investigation import Investigation

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def dashboard(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    invs = (
        await db.execute(
            select(Investigation)
            .where(Investigation.user_id == user.id)
            .order_by(desc(Investigation.created_at))
            .limit(500)
        )
    ).scalars().all()

    total = len(invs)
    threats = Counter(i.threat_level or "unknown" for i in invs)
    kinds = Counter(i.kind for i in invs)
    favorites = sum(1 for i in invs if i.is_favorite)

    # Timeline: per-day count for the last 14 days
    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=d) for d in range(13, -1, -1)]
    timeline = []
    for d in days:
        count = sum(1 for i in invs if i.created_at and i.created_at.date() == d)
        timeline.append({"date": d.isoformat(), "count": count})

    # Country distribution (only IP/email investigations carry country info)
    countries: Counter[str] = Counter()
    for i in invs:
        if i.kind == "ip":
            geo = (i.result or {}).get("geo") or {}
            cc = geo.get("country_code")
            if cc:
                countries[cc] += 1
        elif i.kind == "email":
            # country info not directly available; we attribute to TLD buckets
            tld = (i.target.split("@", 1)[-1].rsplit(".", 1)[-1] or "?").upper()
            countries[tld] += 1

    recent = [
        {
            "id": i.id,
            "kind": i.kind,
            "target": i.target,
            "title": i.title,
            "risk_score": i.risk_score,
            "threat_level": i.threat_level,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in invs[:10]
    ]

    return {
        "stats": {
            "total": total,
            "favorites": favorites,
            "by_kind": dict(kinds.most_common()),
            "by_threat": dict(threats),
        },
        "timeline": timeline,
        "risk_distribution": {
            "low": threats.get("low", 0),
            "medium": threats.get("medium", 0),
            "high": threats.get("high", 0),
            "critical": threats.get("critical", 0),
        },
        "country_distribution": dict(countries.most_common(15)),
        "recent_investigations": recent,
    }
