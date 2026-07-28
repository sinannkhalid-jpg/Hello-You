"""Risk scoring helpers shared across modules.

NOTE: The canonical Risk Score definitions now live in
`app.core.risk`. This file is kept for the `clamp`, `aggregate`,
and `level` helpers still used by some legacy call sites.
"""
from __future__ import annotations

from typing import Iterable


def clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def level(score: int) -> str:
    """Legacy short-token form. Prefer app.core.risk.classify() which
    returns both the canonical name and the color."""
    if score >= 81:
        return "critical"
    if score >= 61:
        return "high"
    if score >= 41:
        return "medium"
    if score >= 21:
        return "guarded"
    return "low"


def aggregate(parts: Iterable[int]) -> int:
    """Combine partial scores: take the max but soften a bit using the average."""
    parts = [p for p in parts if p is not None]
    if not parts:
        return 0
    return clamp(int(max(parts) * 0.7 + (sum(parts) / len(parts)) * 0.3))
