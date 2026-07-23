"""Cached threat intelligence lookups (IP/domain reputation etc.)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ThreatIntelCache(Base):
    __tablename__ = "threat_intel_cache"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    indicator: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    indicator_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    # ip | domain | url | hash | email
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
