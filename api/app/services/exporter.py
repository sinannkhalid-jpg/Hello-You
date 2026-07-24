"""Export helpers: PDF, CSV, JSON."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors


def to_json(data: Any) -> bytes:
    return json.dumps(data, indent=2, default=str).encode("utf-8")


def to_csv(data: dict[str, Any]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["key", "value"])
    def _flatten(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                _flatten(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(value, list):
            if all(isinstance(x, (str, int, float)) for x in value):
                w.writerow([prefix, ", ".join(map(str, value))])
            else:
                for i, v in enumerate(value):
                    _flatten(f"{prefix}[{i}]", v)
        else:
            w.writerow([prefix, value])
    _flatten("", data)
    return buf.getvalue().encode("utf-8")


def to_pdf(data: dict[str, Any]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, title="Hello You Report")
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Hello You — Investigation Report", styles["Title"]))
    story.append(Spacer(1, 12))

    meta = [
        ["Target", str(data.get("target", ""))],
        ["Kind", str(data.get("kind", ""))],
        ["Threat level", str(data.get("threat_level", ""))],
        ["Risk score", f"{data.get('risk_score', 0)}/100"],
        ["Generated at", str(data.get("generated_at", ""))],
    ]
    t = Table(meta, colWidths=[120, 380])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#334155")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    def section(title: str, body: str) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        story.append(Paragraph(body or "—", styles["BodyText"]))
        story.append(Spacer(1, 8))

    section("Executive summary", str(data.get("executive_summary", "")))
    section("Risk assessment", str(data.get("risk_assessment", "")))

    for key, label in [
        ("findings", "Observed findings"),
        ("public_infrastructure", "Public infrastructure"),
        ("recommendations", "Recommendations"),
    ]:
        items = data.get(key, []) or []
        if not items:
            continue
        story.append(Paragraph(label, styles["Heading2"]))
        for it in items:
            story.append(Paragraph(f"• {it}", styles["BodyText"]))
        story.append(Spacer(1, 6))

    mitre = data.get("mitre_attack", []) or []
    if mitre:
        story.append(Paragraph("MITRE ATT&amp;CK mapping", styles["Heading2"]))
        for m in mitre:
            story.append(Paragraph(
                f"• <b>{m.get('id')}</b> — {m.get('name')} <i>({m.get('tactic')})</i>",
                styles["BodyText"],
            ))
        story.append(Spacer(1, 6))

    doc.build(story)
    return buf.getvalue()
