"""
Orchestrator — runs providers concurrently and combines results.

The orchestrator is the only piece of code the rest of the app talks to.
It owns:
  • the shared cache
  • the rate-limiter registry
  • provider instances (created once at app startup)
  • the public `investigate(kind, target)` method

New providers can be added by editing
`app.services.providers.registry.PROVIDER_REGISTRY` — no other code
changes needed.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import BaseProvider, ProviderResult
from app.services.providers.cache import ResponseCache
from app.services.providers.ratelimit import TokenBucketRegistry
from app.services.providers.registry import ALL_PROVIDERS, PROVIDER_REGISTRY

log = get_logger("orchestrator")


# --------------------------------------------------------------------------- #
# Normalized summary
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class Summary:
    risk: str = "low"
    score: int = 0
    malicious: int = 0
    suspicious: int = 0
    threat_level: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk": self.risk,
            "score": self.score,
            "malicious": self.malicious,
            "suspicious": self.suspicious,
            "threat_level": self.threat_level,
        }


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
class Orchestrator:
    def __init__(self) -> None:
        self.cache = ResponseCache(max_entries=5000)
        self.rate_limiter = TokenBucketRegistry()
        self.providers: dict[str, BaseProvider] = {}
        self._build_providers()

    # ---- construction ---------------------------------------------------- #
    def _build_providers(self) -> None:
        # First, auto-discover any extra providers from env (Shodan, Censys, etc.)
        from app.services.providers.registry import autodiscover
        from app.services.providers.base import BaseProvider

        autodiscover()

        for cls in ALL_PROVIDERS:
            inst = cls()
            inst.cache = self.cache
            inst.rate_limiter = self.rate_limiter
            inst.api_key = self._resolve_api_key(cls, inst)
            # Enforce the global hard cap on per-call timeouts. The base
            # class defaults to 5s; this clamp protects against any provider
            # that declares a larger value.
            cap = BaseProvider.MAX_TIMEOUT_SECONDS
            if inst.timeout_seconds > cap:
                log.debug(
                    "provider %s timeout %.1fs > cap %.1fs — clamping",
                    cls.name, inst.timeout_seconds, cap,
                )
                inst.timeout_seconds = cap
            # If the provider requires a key but we don't have one, skip it gracefully
            if inst.requires_key and not inst.api_key:
                inst.enabled = False
                log.info("provider %s disabled (no API key)", cls.name)
            self.providers[cls.name] = inst
            log.info(
                "provider %s ready (enabled=%s, kind=%s, has_key=%s)",
                cls.name, inst.enabled, inst.kind, bool(inst.api_key),
            )

    def _resolve_api_key(self, cls, inst) -> str | None:
        """Auto-load API keys from environment.

        Convention:
          • `<NAME>_API_KEY` — the standard name for any provider
          • `<NAME>_API_ID`  + `<NAME>_API_SECRET` — for two-token providers (Censys)

        A provider may also override its `api_key_env` / `api_id_env` /
        `api_secret_env` class attributes to point to specific env names.
        """
        import os

        name = cls.name.upper()
        # Explicit overrides
        env_name = getattr(cls, "api_key_env", None) or f"{name}_API_KEY"
        key = os.getenv(env_name)
        if key:
            return key

        # Two-token auth (e.g. Censys)
        id_env = getattr(cls, "api_id_env", None) or f"{name}_API_ID"
        secret_env = getattr(cls, "api_secret_env", None) or f"{name}_API_SECRET"
        id_key = os.getenv(id_env) or os.getenv(f"{name}_API_KEY")
        secret = os.getenv(secret_env)
        if id_key and secret:
            return f"{id_key}:{secret}"

        # Backward-compat legacy keys
        legacy = {
            "virustotal": settings.virustotal_api_key,
            "abuseipdb":  settings.abuseipdb_api_key,
            "leakcheck":  settings.leakcheck_api_key,
            "ipapi":      settings.ipapi_key,
            "hibp":       settings.hibp_api_key,
        }
        return legacy.get(cls.name)

    # ---- public API ------------------------------------------------------ #
    async def investigate(
        self,
        kind: str,
        target: str,
        *,
        providers: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Run all providers for the given kind concurrently.

        Returns the normalized aggregate response.
        """
        t0 = time.perf_counter()
        selected = self._select_providers(kind, providers)
        if not selected:
            return {
                "target": target,
                "kind": kind,
                "providers": {},
                "summary": Summary().to_dict(),
                "meta": {
                    "duration_ms": 0,
                    "providers_queried": 0,
                    "providers_ok": 0,
                    "providers_failed": 0,
                },
            }

        tasks = [p.run(target, **kwargs) for p in selected]
        raw: list[ProviderResult] = await asyncio.gather(*tasks, return_exceptions=False)

        by_source: dict[str, dict[str, Any]] = {}
        summary = Summary()
        for r in raw:
            by_source[r.source] = r.to_dict()
            if r.ok:
                d = r.data or {}
                summary.malicious += int(d.get("malicious", 0) or 0)
                summary.suspicious += int(d.get("suspicious", 0) or 0)
                if "score" in d and isinstance(d["score"], (int, float)):
                    summary.score = max(summary.score, int(d["score"]))
        summary.score = min(100, summary.score)
        summary.risk = _risk_band(summary.score)
        summary.threat_level = summary.risk

        elapsed = int((time.perf_counter() - t0) * 1000)
        ok = sum(1 for r in raw if r.ok)

        return {
            "target": target,
            "kind": kind,
            "providers": by_source,
            "summary": summary.to_dict(),
            "meta": {
                "duration_ms": elapsed,
                "providers_queried": len(raw),
                "providers_ok": ok,
                "providers_failed": len(raw) - ok,
            },
        }

    def _select_providers(self, kind: str, names: list[str] | None) -> list[BaseProvider]:
        wanted_classes = PROVIDER_REGISTRY.get(kind, [])
        chosen: list[BaseProvider] = []
        for cls in wanted_classes:
            inst = self.providers.get(cls.name)
            if inst is None or not inst.enabled:
                continue
            if names and inst.name not in names:
                continue
            chosen.append(inst)
        return chosen

    # ---- introspection -------------------------------------------------- #
    def list_providers(self) -> list[dict[str, Any]]:
        return [
            {
                "name": p.name,
                "kind": p.kind,
                "enabled": p.enabled,
                "requires_key": p.requires_key,
                "has_key": bool(p.api_key),
                "rate_limit_per_minute": p.rate_limit_per_minute,
                "cache_ttl": p.cache_ttl,
            }
            for p in self.providers.values()
        ]

    def stats(self) -> dict[str, Any]:
        return {
            "cache": self.cache.stats(),
            "rate_limit": self.rate_limiter.snapshot(),
        }


def _risk_band(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


# --------------------------------------------------------------------------- #
# Module-level singleton
# --------------------------------------------------------------------------- #
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
