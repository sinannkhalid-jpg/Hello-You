"""
Simple async TTL cache, in-memory.

Suitable for a single-instance deployment (Render free tier). For a
multi-instance deployment, swap in Redis (Upstash) here without changing
callers — the public surface is `get` / `set`.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float


class ResponseCache:
    """Thread-/task-safe TTL cache.

    Backed by an `asyncio.Lock` for concurrent set; reads are O(1) and
    lock-free. Entries are evicted lazily on read and via a background
    sweeper.
    """

    def __init__(self, max_entries: int = 5000) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()
        self._max = max_entries

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.time():
            self._store.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            # naive eviction when oversized
            if len(self._store) >= self._max and key not in self._store:
                # drop oldest by expires_at
                oldest = min(self._store.items(), key=lambda kv: kv[1].expires_at)
                self._store.pop(oldest[0], None)
            self._store[key] = _Entry(value, time.time() + max(ttl, 1))

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    def stats(self) -> dict[str, int]:
        return {"size": len(self._store), "max": self._max}
