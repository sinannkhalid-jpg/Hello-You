"""
Email OSINT — only public signals (MX, SPF, DKIM, DMARC, Gravatar, HIBP if keyed).

All helpers are sync, except `hibp_breaches` and `gravatar_exists` which
are async. The FastAPI router calls `gravatar_exists` via
`asyncio.to_thread()` so we never nest an event loop inside another.
"""
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


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def split_email(email: str) -> tuple[str, str]:
    local, _, domain = email.partition("@")
    if not local or not domain:
        raise ValueError("Invalid email address")
    return local, domain.lower()


# --------------------------------------------------------------------------- #
# Gravatar
# --------------------------------------------------------------------------- #
# Use MD5 — this is what Gravatar's avatar URL uses. (Earlier code mixed
# MD5 and SHA256 which produced a hash mismatch.)
def gravatar_hash(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


def gravatar_url(email: str) -> str:
    return f"https://www.gravatar.com/avatar/{gravatar_hash(email)}?d=404"


async def gravatar_exists(email: str) -> bool:
    """Async Gravatar existence check. Returns True if the avatar exists
    (HTTP 200), False otherwise. Never raises — errors are treated as
    'unknown' (False)."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(gravatar_url(email), follow_redirects=True)
            return r.status_code == 200
    except Exception as e:  # noqa: BLE001
        log.debug("gravatar_exists error for %s: %s", email, e)
        return False


async def gravatar_profile(email: str) -> dict[str, Any] | None:
    """Optional: fetch the public Gravatar profile JSON for an email.
    Returns None if no profile is set."""
    try:
        data = await get_json(f"https://www.gravatar.com/{gravatar_hash(email)}.json")
    except Exception as e:  # noqa: BLE001
        log.debug("gravatar_profile error for %s: %s", email, e)
        return None
    if not data or not isinstance(data, dict):
        return None
    entries = data.get("entry") or []
    return entries[0] if entries else None


# --------------------------------------------------------------------------- #
# DNS-based email auth
# --------------------------------------------------------------------------- #
def spf_record(domain: str) -> str | None:
    try:
        for t in lookup_txt(domain):
            if t.lower().startswith("v=spf1"):
                return t
    except Exception as e:  # noqa: BLE001
        log.debug("spf_record error for %s: %s", domain, e)
    return None


def dkim_record(domain: str, selector: str = "default") -> str | None:
    # Try a few common selectors.
    selectors = (selector, "google", "selector1", "selector2", "k1", "s1", "dkim", "mail")
    try:
        for sel in selectors:
            try:
                records = lookup_txt(f"{sel}._domainkey.{domain}")
            except Exception:
                continue
            for t in records:
                if "v=DKIM1" in t or "k=rsa" in t:
                    return t
    except Exception as e:  # noqa: BLE001
        log.debug("dkim_record error for %s: %s", domain, e)
    return None


def dmarc_record(domain: str) -> str | None:
    try:
        for t in lookup_txt(f"_dmarc.{domain}"):
            if t.lower().startswith("v=dmarc1"):
                return t
    except Exception as e:  # noqa: BLE001
        log.debug("dmarc_record error for %s: %s", domain, e)
    return None


# --------------------------------------------------------------------------- #
# HIBP (optional)
# --------------------------------------------------------------------------- #
async def hibp_breaches(email: str) -> dict[str, Any] | list[Any] | None:
    """HaveIBeenPwned breach lookup. Requires a key in env.

    Returns the breach list on success, an empty list for "no breaches
    found", or None if the request fails or no key is configured.
    """
    if not settings.hibp_api_key:
        return None
    try:
        data = await get_json(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}",
            params={"truncateResponse": "false"},
            headers={
                "hibp-api-key": settings.hibp_api_key,
                "User-Agent": "HelloYou-OSINT/1.0 (+educational)",
            },
        )
        return data
    except Exception as e:  # noqa: BLE001
        log.debug("hibp_breaches error for %s: %s", email, e)
        return None


# --------------------------------------------------------------------------- #
# Disposable domain check
# --------------------------------------------------------------------------- #
def disposable_domain(domain: str) -> bool:
    ext = tldextract.extract(domain)
    root = ".".join(p for p in (ext.domain, ext.suffix) if p)
    known = {
        "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
        "throwawaymail.com", "yopmail.com", "trashmail.com", "dispostable.com",
        "maildrop.cc", "sharklasers.com", "guerrillamailblock.com",
        "fakeinbox.com", "mailcatch.com", "tempr.email",
    }
    return root in known


# --------------------------------------------------------------------------- #
# Risk scoring
# --------------------------------------------------------------------------- #
def risk_score(
    email: str,
    mx: list[dict[str, Any]],
    spf: str | None,
    dkim: str | None,
    dmarc: str | None,
    breach: dict | list | None,
    gravatar: bool,
) -> int:
    score = 0
    try:
        domain = email.split("@", 1)[1]
    except IndexError:
        return 0
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
        # HIBP returns a list of breaches; if non-empty we have exposure
        if isinstance(breach, list) and breach:
            score += 20
        elif isinstance(breach, dict) and breach:
            score += 20
    if not gravatar:
        score += 2
    return min(score, 100)
