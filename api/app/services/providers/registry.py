"""
Provider registry.

Maps a target `kind` → list of provider classes that should be queried
for it. Adding a new provider is one of two things:

  1. Drop a `app/services/providers/<name>.py` file containing a class
     that subclasses `BaseProvider` (and exports it as either
     `PROVIDER_CLASS` or as the first `BaseProvider` subclass).

  2. Set the env var `OSINT_EXTRA_PROVIDERS=shodan,censys` (comma-separated
     module names that live under `app.services.providers.*`) and the
     orchestrator will auto-import them at startup.

No other code changes are needed — the new providers will appear in
`/api/v1/intel/providers`, in the registered kinds, in
`/api/v1/intel/stats`, and in `/api/v1/intel/health`.
"""
from __future__ import annotations

import logging
import os

from app.services.providers.abuseipdb import AbuseIPDBProvider
from app.services.providers.censys import CensysProvider
from app.services.providers.crtsh import CrtshProvider
from app.services.providers.dns import DNSProvider
from app.services.providers.gravatar import GravatarProvider
from app.services.providers.hibp import HIBPProvider
from app.services.providers.intelx import IntelXProvider
from app.services.providers.ipapi import IPAPIProvider
from app.services.providers.leakcheck import LeakCheckProvider
from app.services.providers.securitytrails import SecurityTrailsProvider
from app.services.providers.shodan import ShodanProvider
from app.services.providers.username import UsernameProvider
from app.services.providers.virustotal import VirusTotalProvider
from app.services.providers.whois import WhoisProvider

log = logging.getLogger("registry")

# Map: target kind → list of provider classes.
PROVIDER_REGISTRY: dict[str, list[type]] = {
    "domain":   [VirusTotalProvider, CrtshProvider, DNSProvider, WhoisProvider, SecurityTrailsProvider, IntelXProvider],
    "ip":       [AbuseIPDBProvider, IPAPIProvider, VirusTotalProvider, ShodanProvider, CensysProvider],
    "email":    [LeakCheckProvider, HIBPProvider, GravatarProvider],
    "username": [UsernameProvider],
    "url":      [VirusTotalProvider],
}

# All providers, in the order they should appear in the registry output.
ALL_PROVIDERS: list[type] = [
    VirusTotalProvider,
    AbuseIPDBProvider,
    IPAPIProvider,
    CrtshProvider,
    LeakCheckProvider,
    HIBPProvider,
    GravatarProvider,
    SecurityTrailsProvider,
    UsernameProvider,
    DNSProvider,
    WhoisProvider,
    ShodanProvider,
    CensysProvider,
    IntelXProvider,
]

# Already-resolved provider class registry; used as a fast-path check.
_RESOLVED: set[type] = set(ALL_PROVIDERS)


def autodiscover() -> None:
    """Auto-import provider modules listed in `OSINT_EXTRA_PROVIDERS`.

    Format: `OSINT_EXTRA_PROVIDERS=shodan,censys,intelx,securitytrails`
    For each name, the orchestrator will try to import
    `app.services.providers.<name>` and look for `PROVIDER_CLASS` (or
    the first `BaseProvider` subclass defined in the module). The class
    is then added to `ALL_PROVIDERS` and to `PROVIDER_REGISTRY[<its kind>]`.

    Safe to call multiple times.
    """
    raw = os.getenv("OSINT_EXTRA_PROVIDERS", "").strip()
    if not raw:
        return
    from app.services.providers.base import BaseProvider  # local import to avoid cycle
    for name in (n.strip() for n in raw.split(",") if n.strip()):
        try:
            module = __import__(
                f"app.services.providers.{name}",
                fromlist=["PROVIDER_CLASS", "Provider"],
            )
        except Exception as e:  # noqa: BLE001
            log.warning("OSINT_EXTRA_PROVIDERS: failed to import %s: %s", name, e)
            continue
        cls = getattr(module, "PROVIDER_CLASS", None)
        if cls is None:
            for v in vars(module).values():
                if isinstance(v, type) and issubclass(v, BaseProvider) and v is not BaseProvider:
                    cls = v
                    break
        if cls is None:
            log.warning("OSINT_EXTRA_PROVIDERS: %s has no BaseProvider subclass", name)
            continue
        if cls in _RESOLVED:
            continue
        _RESOLVED.add(cls)
        ALL_PROVIDERS.append(cls)
        kind = getattr(cls, "kind", "domain")
        PROVIDER_REGISTRY.setdefault(kind, []).append(cls)
        log.info("OSINT_EXTRA_PROVIDERS: registered %s (kind=%s)", cls.name, kind)
