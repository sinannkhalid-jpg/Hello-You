"""
Censys provider.

Censys migrated to the new Platform API in 2024. The current provider
supports both authentication methods:

  1. **New** — Personal Access Token (PAT) via the Platform API v3:
        ENV:       CENSYS_PAT
        Header:    `Authorization: Bearer <PAT>`
        Endpoint:  https://api.platform.censys.io/v3/global/host/{ip}

  2. **Legacy** — API ID + API Secret via the v1 Search API:
        ENV:       CENSYS_API_ID + CENSYS_API_SECRET
        Header:    `Authorization: Basic <base64(id:secret)>`
        Endpoint:  https://search.censys.io/api/v1/view/ipv4/{ip}

If `CENSYS_PAT` is set, the new API is used. Otherwise, if both legacy
env vars are set, the legacy API is used. Otherwise, the provider is
auto-disabled.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


@dataclass
class _Auth:
    """Resolved authentication for the Censys provider."""

    mode: str                     # "pat" or "legacy"
    token: str                    # raw PAT or base64(id:secret)
    base_url: str                 # API root
    host_path: str                # path template with {ip}
    account_url: str              # health-check endpoint

    @property
    def authorization(self) -> str:
        if self.mode == "pat":
            return f"Bearer {self.token}"
        return f"Basic {self.token}"


def _resolve_auth() -> _Auth | None:
    """Pick the best available auth from the environment.

    Order of preference:
      1. CENSYS_PAT   → new Platform API v3
      2. CENSYS_API_ID + CENSYS_API_SECRET → legacy Search API v1
    """
    pat = os.getenv("CENSYS_PAT", "").strip()
    if pat:
        return _Auth(
            mode="pat",
            token=pat,
            base_url="https://api.platform.censys.io/v3",
            host_path="/global/host/{ip}",
            account_url="https://api.platform.censys.io/v3/account",
        )

    api_id = os.getenv("CENSYS_API_ID", "").strip()
    api_secret = os.getenv("CENSYS_API_SECRET", "").strip()
    if api_id and api_secret:
        token = base64.b64encode(f"{api_id}:{api_secret}".encode()).decode()
        return _Auth(
            mode="legacy",
            token=token,
            base_url="https://search.censys.io/api/v1",
            host_path="/view/ipv4/{ip}",
            account_url="https://search.censys.io/api/v1/account",
        )
    return None


class CensysProvider(BaseProvider):
    name = "censys"
    kind = "ip"
    enabled = True
    requires_key = True
    # Standard token env name (read first, preferred). The orchestrator
    # will see this class attribute and load CENSYS_PAT when available.
    api_key_env = "CENSYS_PAT"
    # Legacy env names — the orchestrator checks api_id_env/api_secret_env
    # only if the primary key is missing.
    api_id_env = "CENSYS_API_ID"
    api_secret_env = "CENSYS_API_SECRET"
    rate_limit_per_minute = 30
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 5.0
    # Health URL is selected dynamically inside `_health_target()` based
    # on the resolved auth mode (PAT → v3, legacy → v1). Do not set a
    # class-level `health_url` here — the override below takes over.

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Pick auth at instance time so the same provider class can
        # transparently switch between PAT and legacy at startup.
        self._auth: _Auth | None = _resolve_auth()
        if self._auth is not None and not self.api_key:
            # The orchestrator may have already set api_key from CENSYS_PAT
            # (or from legacy). Keep _auth in sync with that.
            if self._auth.mode == "pat":
                self.api_key = self._auth.token
            # For legacy, the orchestrator passes "id:secret" as api_key.

    # ------------------------------------------------------------------ #
    # OSINT lookup
    # ------------------------------------------------------------------ #
    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        auth = self._auth or _resolve_auth()
        if auth is None:
            return {
                "found": False,
                "ip": target,
                "auth_mode": "none",
                "extra": {
                    "reason": "censys requires CENSYS_PAT (new) "
                              "or CENSYS_API_ID + CENSYS_API_SECRET (legacy)",
                },
            }

        url = f"{auth.base_url}{auth.host_path.format(ip=target)}"
        data = await get_json(
            url,
            headers={
                "Authorization": auth.authorization,
                "Accept": "application/json",
            },
        )
        if not data or not isinstance(data, dict):
            return {
                "found": False,
                "ip": target,
                "auth_mode": auth.mode,
                "extra": {"reason": "no data"},
            }

        # The v3 Platform API wraps the host in a `result` envelope:
        #   {"result": {"ip": "...", "services": [...], "location": {...}, ...}}
        # The legacy v1 Search API returns the host object directly.
        if auth.mode == "pat" and "result" in data and isinstance(data["result"], dict):
            host = data["result"]
        else:
            host = data

        return self._normalize(target, host, auth.mode)

    # ------------------------------------------------------------------ #
    # Normalization — produce the same shape regardless of API version
    # ------------------------------------------------------------------ #
    def _normalize(self, target: str, host: dict[str, Any], mode: str) -> dict[str, Any]:
        # Both API versions use roughly the same nested shape, but the v3
        # API uses `services` and the v1 API uses `ports` (with nested dicts).
        ports: list[int] = []
        for p in host.get("ports", []) or []:
            if isinstance(p, dict) and isinstance(p.get("port"), int):
                ports.append(p["port"])
            elif isinstance(p, int):
                ports.append(p)
        if not ports:
            for svc in host.get("services", []) or []:
                if isinstance(svc, dict):
                    port = svc.get("port")
                    if isinstance(port, int):
                        ports.append(port)
        ports = sorted(set(ports))

        as_data = host.get("autonomous_system") or {}
        loc = host.get("location") or {}
        protocols = host.get("protocols") or []
        if not protocols and host.get("services"):
            protocols = sorted({
                s.get("protocol")
                for s in (host.get("services") or [])
                if isinstance(s, dict) and s.get("protocol")
            })

        return {
            "found": True,
            "ip": target,
            "auth_mode": mode,
            "asn": as_data.get("asn") or host.get("asn"),
            "asn_org": (
                as_data.get("name")
                or as_data.get("description")
                or host.get("asn_org")
            ),
            "country": loc.get("country") or host.get("location", {}).get("country_code"),
            "city": loc.get("city") or host.get("location", {}).get("city"),
            "ports": ports,
            "operating_system": host.get("operating_system") or host.get("os"),
            "services_count": len(ports),
            "extra": {
                "protocols": protocols,
                "asn_country": as_data.get("country"),
                "censys_api": "v3" if mode == "pat" else "v1",
            },
        }

    # ------------------------------------------------------------------ #
    # Health check — uses the right endpoint for the current auth mode
    # ------------------------------------------------------------------ #
    async def _health_target(self) -> Any:
        auth = self._auth or _resolve_auth()
        if auth is None:
            return False
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(
                auth.account_url,
                headers={
                    "Authorization": auth.authorization,
                    "Accept": "application/json",
                },
            )
            return r.status_code < 500


PROVIDER_CLASS = CensysProvider
