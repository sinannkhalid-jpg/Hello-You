"""
Provider architecture for Hello You.

Every OSINT source implements the `BaseProvider` interface. Providers are
isolated, independently testable, and fault-tolerant: an error in one
provider never prevents others from returning data.

The orchestrator (`app.services.orchestrator`) runs providers concurrently
with `asyncio.gather(return_exceptions=True)`, applies caching, and returns
a normalized aggregate response.
"""
from __future__ import annotations

import abc
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar

from app.core.logging import get_logger

log = get_logger("provider")


def _confidence(data: dict[str, Any]) -> float:
    """Derive a 0..1 confidence value from a provider's data dict.

    Conventions used by providers:
      • `confidence` (0..1) — direct
      • `score` (0..100)    — divide by 100
      • `abuse_confidence`  — divide by 100
    Otherwise we fall back to 1.0 on success, 0.0 on no-data.
    """
    if not isinstance(data, dict):
        return 0.0
    c = data.get("confidence")
    if isinstance(c, (int, float)):
        v = float(c)
        return max(0.0, min(1.0, v if v <= 1.0 else v / 100.0))
    for k in ("score", "abuse_confidence"):
        s = data.get(k)
        if isinstance(s, (int, float)):
            return max(0.0, min(1.0, float(s) / 100.0))
    return 1.0 if data else 0.0


# --------------------------------------------------------------------------- #
# Data types
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class ProviderResult:
    """Standardized wrapper around a single provider's output.

    `ok`         - whether the provider returned useful data
    `data`       - the normalized response (provider-defined shape)
    `error`      - error message if the call failed
    `cached`     - True if this came from cache
    `duration_ms`- how long the call took
    `source`     - the provider name (e.g. "virustotal")
    """
    source: str
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cached: bool = False
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical envelope.

        Every provider result includes the same top-level fields:
            provider, found, ok, error, cached, response_time_ms,
            data, confidence
        so the frontend can render them uniformly.
        """
        d = self.data or {}
        return {
            "provider": self.source,
            "ok": self.ok,
            "found": bool(d.get("found", self.ok)),
            "error": self.error,
            "cached": self.cached,
            "response_time_ms": self.duration_ms,
            "confidence": _confidence(d),
            "data": d,
        }


# --------------------------------------------------------------------------- #
# Base provider
# --------------------------------------------------------------------------- #
class BaseProvider(abc.ABC):
    """Abstract base class for all OSINT providers.

    Subclasses must set `name` and implement `lookup(target, **kwargs)`.
    Optional overrides: `enabled`, `requires_key`, `cache_ttl`,
    `rate_limit_per_minute`.
    """

    # ---- class-level configuration (override in subclasses) ----
    name: ClassVar[str] = ""
    kind: ClassVar[str] = ""           # e.g. "domain", "ip", "email", "username"
    enabled: ClassVar[bool] = True
    requires_key: ClassVar[bool] = False
    cache_ttl: ClassVar[int] = 60 * 30  # 30 min default
    rate_limit_per_minute: ClassVar[int] = 60
    # Per-call hard cap. Every provider runs under asyncio.wait_for() with
    # this timeout. The orchestrator additionally enforces a 5s cap.
    timeout_seconds: ClassVar[float] = 5.0
    max_retries: ClassVar[int] = 2

    # Hard upper bound for any provider timeout, regardless of what the
    # class declares. Required by the production spec.
    MAX_TIMEOUT_SECONDS: ClassVar[float] = 5.0

    # ---- per-instance deps, set by the orchestrator ----
    cache: Any = None           # app.services.providers.cache.ResponseCache
    rate_limiter: Any = None    # app.services.providers.ratelimit.TokenBucketRegistry
    api_key: str | None = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise ValueError(f"{cls.__name__} must set class attribute `name`")

    # ------------------------------------------------------------------ #
    # Public entry point — wraps lookup() with cache, rate limit, retry
    # ------------------------------------------------------------------ #
    async def run(self, target: str, **kwargs: Any) -> ProviderResult:
        t0 = time.perf_counter()

        if not self.enabled:
            return ProviderResult(self.name, False, error="provider disabled", duration_ms=0)

        if self.requires_key and not self.api_key:
            return ProviderResult(self.name, False, error="API key not configured", duration_ms=0)

        # Rate limit
        if self.rate_limiter and not await self.rate_limiter.allow(self.name, self.rate_limit_per_minute):
            return ProviderResult(self.name, False, error="rate limited", duration_ms=0)

        # Cache lookup
        cache_key = self._cache_key(target, kwargs)
        if self.cache and cache_key:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                ms = int((time.perf_counter() - t0) * 1000)
                # Ensure `found` is set on cached data
                if isinstance(cached, dict) and "found" not in cached:
                    cached = {**cached, "found": bool(cached)}
                return ProviderResult(self.name, True, data=cached, cached=True, duration_ms=ms)

        # Provider call with retry
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                data = await asyncio.wait_for(
                    self.lookup(target, **kwargs),
                    timeout=self.timeout_seconds,
                )
                data = data or {}
                if self.cache and cache_key:
                    await self.cache.set(cache_key, data, ttl=self.cache_ttl)
                ms = int((time.perf_counter() - t0) * 1000)
                return ProviderResult(self.name, True, data=data, duration_ms=ms)
            except asyncio.TimeoutError:
                last_exc = asyncio.TimeoutError(f"timeout after {self.timeout_seconds}s")
                log.warning("provider %s timeout (attempt %d) for %s", self.name, attempt + 1, target)
            except Exception as e:  # noqa: BLE001
                last_exc = e
                log.warning("provider %s error (attempt %d) for %s: %s", self.name, attempt + 1, target, e)
            # exponential backoff
            if attempt < self.max_retries:
                await asyncio.sleep(0.3 * (2 ** attempt))

        ms = int((time.perf_counter() - t0) * 1000)
        return ProviderResult(self.name, False, error=str(last_exc) or "unknown error", duration_ms=ms)

    # ------------------------------------------------------------------ #
    # Subclass hook
    # ------------------------------------------------------------------ #
    @abc.abstractmethod
    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        """Perform the actual lookup. Return a normalized dict."""

    async def healthcheck(self) -> dict[str, Any]:
        """Optional lightweight probe used by /intel/health.

        Default: do a benign lookup against a known-valid target with
        a short timeout. Providers can override.
        """
        t0 = time.perf_counter()
        try:
            r = await asyncio.wait_for(self._health_target(), timeout=4.0)
            return {
                "ok": bool(r),
                "duration_ms": int((time.perf_counter() - t0) * 1000),
                "detail": r if isinstance(r, (str, dict, list)) else None,
            }
        except asyncio.TimeoutError:
            return {"ok": False, "duration_ms": int((time.perf_counter() - t0) * 1000), "detail": "timeout"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "duration_ms": int((time.perf_counter() - t0) * 1000), "detail": str(e)[:160]}

    async def _health_target(self) -> Any:
        """Default: ping `health_url` if set, otherwise no-op success.

        Providers can override for more meaningful probes.
        """
        import httpx
        url = getattr(self, "health_url", None)
        if not url:
            return True
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(url, follow_redirects=True)
            return r.status_code < 500

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _cache_key(self, target: str, kwargs: dict[str, Any]) -> str:
        if kwargs:
            return f"{self.name}:{target}:{sorted(kwargs.items())}"
        return f"{self.name}:{target}"
