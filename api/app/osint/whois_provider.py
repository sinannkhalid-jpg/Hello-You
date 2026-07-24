"""RDAP (Registration Data Access Protocol) lookups.

RDAP is the IETF standard replacement for WHOIS. It returns structured JSON
over HTTPS from regional internet registries. We prefer RDAP; we only fall
back to a thin-WHOIS TCP query if the registry has no RDAP endpoint.

Source: IANA RDAP bootstrap, https://data.iana.org/rdap/
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.osint.http import get_json

log = get_logger(__name__)

# IANA RDAP bootstrap (fetched lazily; cached at module level)
_BOOTSTRAP: dict[str, list[str]] | None = None


async def _bootstrap() -> dict[str, list[str]]:
    global _BOOTSTRAP
    if _BOOTSTRAP is not None:
        return _BOOTSTRAP
    data = await get_json("https://data.iana.org/rdap/dns.json")
    services: dict[str, list[str]] = {}
    if isinstance(data, dict):
        # IANA RDAP bootstrap format: services is a list of [ [tlds], [urls] ] pairs
        for entry in data.get("services", []):
            if not isinstance(entry, list) or len(entry) < 2:
                continue
            tld_groups = entry[:-1]
            url_groups = entry[-1]
            urls: list[str] = []
            for u in url_groups if isinstance(url_groups, list) else [url_groups]:
                if isinstance(u, str):
                    urls.append(u)
            for grp in tld_groups:
                if not isinstance(grp, list):
                    continue
                for tld in grp:
                    if isinstance(tld, str):
                        services.setdefault(tld.lower(), []).extend(urls)
    _BOOTSTRAP = services
    return services


async def _rdap_for_domain(domain: str) -> str | None:
    tld = domain.rsplit(".", 1)[-1].lower()
    services = await _bootstrap()
    urls = services.get(tld) or services.get("*")
    if not urls:
        return None
    return urls[0] if isinstance(urls[0], str) else None


def _iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # RDAP: 2024-01-02T03:04:05Z
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


async def rdap_lookup(domain: str) -> dict[str, Any] | None:
    base = await _rdap_for_domain(domain)
    if not base:
        return None
    url = f"{base.rstrip('/')}/domain/{domain}"
    data = await get_json(url)
    if not data:
        return None
    return data


def summarize_rdap(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten a raw RDAP response into our WHOISInfo shape."""
    statuses: list[str] = list(data.get("status", []))
    nameservers: list[str] = []
    for ns in data.get("nameservers", []) or []:
        if isinstance(ns, dict):
            ldh = ns.get("ldhName")
            if isinstance(ldh, list):
                ldh = ldh[0] if ldh else ""
            name = (ldh or "").strip()
            if name:
                nameservers.append(name.lower())
        elif isinstance(ns, str):
            nameservers.append(ns.lower().strip())
    events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events", [])}

    registrar = None
    for ent in data.get("entities", []):
        roles = ent.get("roles", [])
        if "registrar" in roles:
            for card in ent.get("vcardArray", [None, []])[1] or []:
                if card and card[0] == "fn":
                    registrar = card[3]
                    break
        if registrar:
            break

    return {
        "registrar": registrar,
        "registrant": None,  # RDAP redacts registrant contact on most gTLDs
        "created_at": _iso(events.get("registration")),
        "expires_at": _iso(events.get("expiration")),
        "updated_at": _iso(events.get("last changed") or events.get("last update of RDAP database")),
        "nameservers": nameservers,
        "statuses": statuses,
        "source": "rdap",
        "raw": {
            "handle": data.get("handle"),
            "ldhName": data.get("ldhName"),
            "entities_count": len(data.get("entities", [])),
        },
    }
