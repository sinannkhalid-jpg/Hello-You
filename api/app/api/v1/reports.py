"""AI-style report generation + export (PDF/CSV/JSON)."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.investigation import Investigation
from app.models.report import Report
from app.schemas.osint import AIReport, AIReportRequest
from app.services.ai_report import generate_report
from app.services.exporter import to_csv, to_json, to_pdf

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=AIReport)
async def generate(
    body: AIReportRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = dict(body.context or {})
    if body.investigation_id and not data:
        inv = (
            await db.execute(
                select(Investigation).where(
                    Investigation.id == body.investigation_id,
                    Investigation.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if not inv:
            raise HTTPException(404, "Investigation not found")
        data = inv.result or {}
        body.target = body.target or inv.target
        body.kind = body.kind or inv.kind

    report = generate_report(body.target, body.kind, data)
    db.add(
        Report(
            user_id=user.id,
            investigation_id=body.investigation_id,
            title=f"Report — {body.kind}: {body.target}",
            format="json",
            content=report,
        )
    )
    return AIReport(**report)


@router.get("/export/{inv_id}")
async def export_inv(
    inv_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    fmt: Literal["pdf", "csv", "json"] = "pdf",
):
    inv = (
        await db.execute(
            select(Investigation).where(
                Investigation.id == inv_id, Investigation.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Investigation not found")

    payload = generate_report(inv.target, inv.kind, inv.result or {})
    if fmt == "pdf":
        data = to_pdf(payload)
        media = "application/pdf"
        filename = f"report-{inv.kind}-{inv.target}.pdf"
    elif fmt == "csv":
        data = to_csv(payload)
        media = "text/csv"
        filename = f"report-{inv.kind}-{inv.target}.csv"
    else:
        data = to_json(payload)
        media = "application/json"
        filename = f"report-{inv.kind}-{inv.target}.json"

    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
