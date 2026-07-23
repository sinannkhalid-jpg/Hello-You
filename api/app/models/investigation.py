"""Investigation + search history model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Investigation(Base):
    """Every OSINT query a user runs is stored as an investigation.

    The `kind` field stores the module name (username, email, phone, domain,
    ip, dns, whois, ssl, subdomain, technology, etc.). The `target` is the
    value the user looked up. The `result` JSON holds the structured response.
    """

    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    kind: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    threat_level: Mapped[str | None] = mapped_column(String(32), nullable=True)

    is_favorite: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
