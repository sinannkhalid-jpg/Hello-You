"""Email OSINT — only public signals (MX, SPF, DKIM, DMARC, Gravatar, HIBP if keyed)."""
from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import quote

import tldextract  # type: ignore

from app.core.config import settings
from app.core.logging import get_logger
from app.osint.dns_provider import lookup_mx, lookup_txt
from app.osint.http import get_json

log = get_logger(__name__)


def split_email(email: str) -> tuple[str, str]:
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise ValueError("Invalid email address")
    return local, domain.lower()


def gravatar_url(email: str) -> str | None:
    h = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
    return f"https://www.gravatar.com/avatar/{h}?d=404"


def gravatar_exists(email: str) -> bool:
    import asyncio
    import httpx

    async def _check() -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(gravatar_url(email))  # type: ignore[arg-type]
                return r.status_code == 200
        except Exception:
            return False

    return asyncio.run(_check())


def spf_record(domain: str) -> str | None:
    for t in lookup_txt(domain):
        if t.lower().startswith("v=spf1"):
            return t
    return None


def dkim_record(domain: str, selector: str = "default") -> str | None:
    # Try a few common selectors.
    for sel in (selector, "google", "selector1", "selector2", "k1", "s1", "dkim"):
        for t in lookup_txt(f"{sel}._domainkey.{domain}"):
            if "v=DKIM1" in t or "k=rsa" in t:
                return t
    return None


def dmarc_record(domain: str) -> str | None:
    for t in lookup_txt(f"_dmarc.{domain}"):
        if t.lower().startswith("v=dmarc1"):
            return t
    return None


async def hibp_breaches(email: str) -> dict[str, Any] | None:
    """HaveIBeenPwned range/search is deprecated; we only call the breach API
    if a key is provided. Otherwise we return None and the UI shows a neutral
    'no breach data' state."""
    if not settings.hibp_api_key:
        return None
    data = await get_json(
        f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}",
        params={"truncateResponse": "false"},
        headers={"hibp-api-key": settings.hibp_api_key, "User-Agent": "OSINT-Nexus"},
    )
    return data


def disposable_domain(domain: str) -> bool:
    # Tiny built-in list of well-known disposable providers. Not exhaustive.
    ext = tldextract.extract(domain)
    root = ".".join(p for p in (ext.domain, ext.suffix) if p)
    known = {
        "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
        "throwawaymail.com", "yopmail.com", "trashmail.com", "dispostable.com",
    }
    return root in known


def risk_score(email: str, mx: list[dict[str, Any]], spf: str | None,
                dkim: str | None, dmarc: str | None, breach: dict | None,
                gravatar: bool) -> int:
    score = 0
    domain = email.split("@", 1)[1]
    if not mx:
        score += 35
    if not spf:
        score += 10
    if not dkim:
        score += 10
    if not dmarc:
        score += 10
    if disposable_domain(domain):
        score += 25
    if breach:
        score += 20
    if not gravatar:
        score += 2
    return min(score, 100)
