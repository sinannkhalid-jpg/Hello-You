"""Certificate Transparency search via crt.sh (public, free, no key)."""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.osint.http import get_json

log = get_logger(__name__)

CRTSH_URL = "https://crt.sh/"


async def search_certificates(domain: str, limit: int = 100) -> list[dict[str, Any]]:
    """Query crt.sh for certificates logged for `domain` (incl. subdomains)."""
    url = f"{CRTSH_URL}?q={domain}&output=json&dedupe=Y"
    data = await get_json(url, timeout=30)  # crt.sh can be slow
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for row in data[:limit]:
        out.append(
            {
                "id": row.get("id"),
                "issuer_ca_id": row.get("issuer_ca_id"),
                "issuer_name": row.get("issuer_name"),
                "common_name": row.get("common_name"),
                "name_value": row.get("name_value"),
                "not_before": row.get("not_before"),
                "not_after": row.get("not_after"),
                "serial_number": row.get("serial_number"),
            }
        )
    return out


async def discover_subdomains(domain: str, limit: int = 200) -> list[str]:
    """Use CT logs (crt.sh) to find publicly-logged subdomains."""
    certs = await search_certificates(domain, limit=limit)
    found: set[str] = set()
    for c in certs:
        for name in (c.get("name_value") or "").splitlines():
            n = name.strip().lower().lstrip("*.")
            if n.endswith("." + domain) or n == domain:
                found.add(n)
    return sorted(found)
