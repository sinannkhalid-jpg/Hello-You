"""Technology detection via HTTP response headers + a tiny HTML signature set.

We never run JS, never run active probes that could be considered intrusive.
We only inspect what the server already returned to a normal GET.
"""
from __future__ import annotations

from typing import Any

import httpx
import tldextract  # type: ignore

from app.core.logging import get_logger

log = get_logger(__name__)

# (name, category, header_or_html, regex)
_SIGS: list[tuple[str, str, str, str]] = [
    ("Next.js",      "framework", "header",  r"(?i)x-nextjs"),
    ("Next.js",      "framework", "html",    r"_next/static"),
    ("React",        "framework", "html",    r"<div[^>]+data-reactroot"),
    ("Vue.js",       "framework", "html",    r"id=\"app\"[^>]*data-v-|v-cloak"),
    ("Angular",      "framework", "html",    r"<app-root[ >]"),
    ("Nuxt.js",      "framework", "html",    r"_nuxt/"),
    ("SvelteKit",    "framework", "html",    r"/_app/"),
    ("WordPress",    "cms",       "html",    r"wp-content/|wp-includes/"),
    ("Drupal",       "cms",       "header",  r"(?i)x-drupal"),
    ("Joomla",       "cms",       "html",    r"/components/com_"),
    ("Shopify",      "ecommerce", "html",    r"cdn\.shopify\.com"),
    ("Magento",      "ecommerce", "html",    r"/skin/frontend/|Mage\.Cookies"),
    ("Cloudflare",   "cdn",       "header",  r"(?i)server: cloudflare|cloudflare"),
    ("Cloudflare",   "cdn",       "header",  r"(?i)cf-ray"),
    ("Fastly",       "cdn",       "header",  r"(?i)x-served-by:\s*cache-"),
    ("Akamai",       "cdn",       "header",  r"(?i)x-akamai"),
    ("Vercel",       "hosting",   "header",  r"(?i)x-vercel-id"),
    ("Netlify",      "hosting",   "header",  r"(?i)server: netlify|x-nf-"),
    ("AWS",          "hosting",   "header",  r"(?i)x-amz-cf-id|via:\s*S3"),
    ("Nginx",        "server",    "header",  r"(?i)server: nginx"),
    ("Apache",       "server",    "header",  r"(?i)server: apache"),
    ("IIS",          "server",    "header",  r"(?i)server: microsoft-iis"),
    ("PHP",          "language",  "header",  r"(?i)x-powered-by:\s*php"),
    ("ASP.NET",      "language",  "header",  r"(?i)x-powered-by:\s*asp\.net|x-aspnet-version"),
    ("Node.js",      "language",  "header",  r"(?i)x-powered-by:\s*express"),
    ("Express",      "framework", "header",  r"(?i)x-powered-by:\s*express"),
    ("Laravel",      "framework", "html",    r"laravel|/livewire/"),
    ("Django",       "framework", "header",  r"(?i)x-frame-options.*DENY|csrfmiddlewaretoken"),
    ("Bootstrap",    "css",       "html",    r"bootstrap(?:\.min)?\.css"),
    ("Tailwind",     "css",       "html",    r"tailwindcss|tailwind\.css"),
    ("jQuery",       "js",        "html",    r"jquery(?:\.min)?\.js"),
    ("Google Analytics", "analytics", "html", r"googletagmanager\.com|google-analytics\.com"),
    ("Stripe",       "payment",   "html",    r"js\.stripe\.com"),
]


async def detect(url: str) -> list[dict[str, Any]]:
    import re
    from urllib.parse import urlparse

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    host = parsed.netloc or tldextract.extract(url).registered_domain
    if not host:
        return []

    found: dict[str, dict[str, Any]] = {}
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
            follow_redirects=True,
            headers={"User-Agent": "OSINT-Nexus/1.0 (+educational)"},
        ) as client:
            r = await client.get(url)
            headers = {k.lower(): v for k, v in r.headers.items()}
            html = r.text
    except Exception as e:
        log.debug("tech detect failed for %s: %s", url, e)
        return []

    for name, category, kind, pattern in _SIGS:
        if name in found:
            continue
        m = (
            re.search(pattern, headers.get("__raw__", ""))
            if kind == "header" and False  # we'll join all headers below
            else None
        )
        if kind == "header":
            blob = " ".join(f"{k}: {v}" for k, v in headers.items())
            if re.search(pattern, blob):
                found[name] = {"name": name, "category": category, "confidence": 0.9, "evidence": "response headers"}
        else:
            if re.search(pattern, html, re.IGNORECASE):
                found[name] = {"name": name, "category": category, "confidence": 0.7, "evidence": "HTML signature"}

    # Server header alone is a strong signal.
    server = headers.get("server")
    if server and "server" not in found:
        found[server] = {"name": server, "category": "server", "confidence": 0.8, "evidence": "Server header"}

    return list(found.values())
