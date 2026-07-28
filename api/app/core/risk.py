"""
Centralized Risk Score definitions and helpers.

This is the single source of truth for risk classification across
the entire application. The score is interpreted as RISK
(higher = more risky), never as reputation (higher = safer).

Bands (canonical):
    0-20   → "Low Risk"      (green  #22c55e)
    21-40  → "Guarded"       (lime   #84cc16)
    41-60  → "Moderate"      (amber  #f59e0b)
    61-80  → "High Risk"     (orange #f97316)
    81-100 → "Critical"      (red    #ef4444)

Both `risk_score` (0-100 int) and `risk_level` (canonical label)
are returned together by `classify()`.
"""
from __future__ import annotations

from typing import Any

# Canonical bands in priority order (highest risk first).
RISK_BANDS: list[dict[str, Any]] = [
    {"name": "Critical",   "min": 81, "max": 100, "color": "#ef4444", "token": "critical"},
    {"name": "High Risk",  "min": 61, "max": 80,  "color": "#f97316", "token": "high"},
    {"name": "Moderate",   "min": 41, "max": 60,  "color": "#f59e0b", "token": "medium"},
    {"name": "Guarded",    "min": 21, "max": 40,  "color": "#84cc16", "token": "guarded"},
    {"name": "Low Risk",   "min": 0,  "max": 20,  "color": "#22c55e", "token": "low"},
]

# Token → name (for converting old "low" / "medium" / "high" / "critical"
# values returned by other modules into the new canonical names).
LEGACY_TO_NAME = {
    "low":      "Low Risk",
    "guarded":  "Guarded",
    "medium":   "Moderate",
    "high":     "High Risk",
    "critical": "Critical",
}

# Canonical name → legacy token (for clients that read "risk_level"
# and want a short form).
NAME_TO_TOKEN = {b["name"]: b["token"] for b in RISK_BANDS}

# Canonical name → hex color.
NAME_TO_COLOR = {b["name"]: b["color"] for b in RISK_BANDS}

# Canonical name → Tailwind class set (border / bg / text).
NAME_TO_CLASSES = {
    "Critical":   "border-[#ef4444]/30 bg-[#ef4444]/5 text-[#ef4444]",
    "High Risk":  "border-[#f97316]/30 bg-[#f97316]/5 text-[#f97316]",
    "Moderate":   "border-[#f59e0b]/30 bg-[#f59e0b]/5 text-[#f59e0b]",
    "Guarded":    "border-[#84cc16]/30 bg-[#84cc16]/5 text-[#84cc16]",
    "Low Risk":   "border-[#22c55e]/30 bg-[#22c55e]/5 text-[#22c55e]",
}


def classify(score: int | float | None) -> dict[str, Any]:
    """Classify a numeric risk score (0-100) into a band.

    Returns a dict with the canonical fields:
        {
          "risk_score": 0-100 int,
          "risk_level": "Low Risk" | "Guarded" | "Moderate"
                      | "High Risk" | "Critical",
          "color":      "#rrggbb",
        }

    A None / out-of-range score is clamped to 0.
    """
    if score is None:
        s = 0
    else:
        try:
            s = int(score)
        except (TypeError, ValueError):
            s = 0
    s = max(0, min(100, s))
    for b in RISK_BANDS:
        if b["min"] <= s <= b["max"]:
            return {
                "risk_score": s,
                "risk_level": b["name"],
                "color": b["color"],
            }
    # Should not be reachable because of the clamp above, but stay
    # defensive.
    return {"risk_score": s, "risk_level": "Low Risk", "color": "#22c55e"}


def normalize_level(level: str | None) -> str:
    """Map any of the legacy short tokens (low/medium/high/critical/guarded)
    to the canonical full name. Unknown values return 'Moderate' as a
    safe default."""
    if not level:
        return "Moderate"
    k = level.strip().lower()
    if k in LEGACY_TO_NAME:
        return LEGACY_TO_NAME[k]
    # Already canonical?
    for b in RISK_BANDS:
        if b["name"].lower() == k:
            return b["name"]
    return "Moderate"


def classes_for(level: str | None) -> str:
    """Tailwind classes for a given level (canonical name or short token)."""
    name = normalize_level(level)
    return NAME_TO_CLASSES.get(name, NAME_TO_CLASSES["Moderate"])


def color_for(level: str | None) -> str:
    name = normalize_level(level)
    return NAME_TO_COLOR.get(name, "#f59e0b")


def from_legacy_threat_level(threat: str | None) -> str:
    """Map a legacy 'threat_level' value (low/medium/high/critical) to
    the new canonical risk level name. Used during the back-compat
    migration for the existing 'risk_score' and 'threat_level' fields
    on the EmailResult, PhoneResult, etc."""
    return normalize_level(threat)
