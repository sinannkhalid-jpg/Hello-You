"""
Normalized response shapes used across providers.

Each provider returns a dict that conforms to one of these shapes.
The orchestrator wraps them in a ProviderResult and combines them.
"""
from __future__ import annotations

from typing import Any, Literal

ThreatLevel = Literal["low", "medium", "high", "critical", "unknown"]


def normalize_reputation(
    *,
    malicious: int = 0,
    suspicious: int = 0,
    harmless: int = 0,
    undetected: int = 0,
    score: int | None = None,
    threat_level: ThreatLevel | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a normalized reputation dict used by IP / domain / URL providers."""
    if score is None:
        # heuristic: 0..100
        score = min(100, malicious * 25 + suspicious * 8 + max(0, 30 - harmless))
    if threat_level is None:
        if score >= 75:
            threat_level = "critical"
        elif score >= 50:
            threat_level = "high"
        elif score >= 25:
            threat_level = "medium"
        else:
            threat_level = "low"
    out: dict[str, Any] = {
        "malicious": malicious,
        "suspicious": suspicious,
        "harmless": harmless,
        "undetected": undetected,
        "score": score,
        "threat_level": threat_level,
    }
    if extra:
        out["extra"] = extra
    return out
