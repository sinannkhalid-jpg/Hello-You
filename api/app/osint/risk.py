"""Risk scoring helpers shared across modules."""
from __future__ import annotations

from typing import Iterable


def clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


def level(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def aggregate(parts: Iterable[int]) -> int:
    """Combine partial scores: take the max but soften a bit using the average."""
    parts = [p for p in parts if p is not None]
    if not parts:
        return 0
    return clamp(int(max(parts) * 0.7 + (sum(parts) / len(parts)) * 0.3))
