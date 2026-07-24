"""
Per-provider async token-bucket rate limiter.

Each provider gets its own bucket sized to its `rate_limit_per_minute`.
Buckets refill smoothly. A failing provider never consumes a token.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    capacity: float
    refill_per_sec: float
    tokens: float
    last_refill: float


class TokenBucketRegistry:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    def _bucket(self, name: str, per_minute: int) -> _Bucket:
        b = self._buckets.get(name)
        if b is None:
            capacity = max(float(per_minute), 1.0)
            refill = capacity / 60.0
            b = _Bucket(capacity=capacity, refill_per_sec=refill, tokens=capacity, last_refill=time.time())
            self._buckets[name] = b
        return b

    async def allow(self, name: str, per_minute: int) -> bool:
        async with self._lock:
            b = self._bucket(name, per_minute)
            now = time.time()
            elapsed = now - b.last_refill
            b.tokens = min(b.capacity, b.tokens + elapsed * b.refill_per_sec)
            b.last_refill = now
            if b.tokens >= 1:
                b.tokens -= 1
                return True
            return False

    def snapshot(self) -> dict[str, float]:
        return {k: round(v.tokens, 2) for k, v in self._buckets.items()}
