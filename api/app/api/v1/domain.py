"""
Domain / DNS / WHOIS / SSL / Subdomain / Technology routers.

Behavior:
  • Backward compatible: every existing endpoint and response shape is
    preserved.
  • The unified domain investigation now also calls into the new
    provider architecture (DNS, WHOIS, crt.sh, VirusTotal) through
    the orchestrator, with results stored under `providers` in the
    investigation record. The legacy fields are unchanged.
"""
from __future__ import annotations

import time
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.ssl_provider import get_cert
from app.osint.tech_provider import detect as detect_tech
from app.schemas.osint import (
    DNSRecords,
    DomainResult,
    SSLInfo,
    SubdomainResult,
    Technology,
    WHOISInfo,
)
from app.services.investigation_service import save_investigation
from app.services.orchestrator import get_orchestrator
from app.services.serializer import to_jsonable

router = APIRouter(prefix="/domain", tags=["domain"])


def _normalize(domain: str) -> str:
    domain = domain.strip().lower()
    if domain.startswith(("http://", "https://")):
        domain = domain.split("://", 1)[1]
    domain = domain.split("/", 1)[0]
    if not domain or "." not in domain:
        raise HTTPException(400, "Invalid domain")
    return domain


# ---- legacy helpers (unchanged) ------------------------------------------- #
def _legacy_dns(domain: str) -> DNSRecords:
    from app.osint.dns_provider import (
        dnssec_ok, lookup_a, lookup_aaaa, lookup_caa, lookup_mx, lookup_ns,
        lookup_ptr, lookup_soa, lookup_txt,
    )
    return DNSRecords(
        a=lookup_a(domain),
        aaaa=lookup_aaaa(domain),
        mx=lookup_mx(domain),
        ns=lookup_ns(domain),
        txt=lookup_txt(domain),
        cname=[],
        soa=lookup_soa(domain),
        caa=lookup_caa(domain),
        ptr=lookup_ptr(domain) if all(p.isdigit() for p in domain.split(".") if p) else [],
        dnssec=dnssec_ok(domain),
    )


def _legacy_whois(domain: str) -> WHOISInfo | None:
    import asyncio
    from app.osint.whois_provider import rdap_lookup, summarize_rdap
    data = asyncio.get_event_loop().run_until_complete(rdap_lookup(domain)) if False else None
    # rdap_lookup is async; do it properly
    return None  # populated via the async wrapper below


async def _legacy_whois_async(domain: str) -> WHOISInfo | None:
    from app.osint.whois_provider import rdap_lookup, summarize_rdap
    rdap = await rdap_lookup(domain)
    if not rdap:
        return None
    return WHOISInfo(**summarize_rdap(rdap))


def _legacy_ssl(domain: str) -> SSLInfo | None:
    cert = get_cert(domain)
    if not cert:
        return None
    return SSLInfo(
        issuer=cert.get("issuer"),
        subject=cert.get("subject"),
        valid_from=cert.get("valid_from"),
        valid_to=cert.get("valid_to"),
        days_remaining=cert.get("days_remaining"),
        fingerprint_sha256=cert.get("fingerprint_sha256"),
        public_key_algorithm=cert.get("public_key_algorithm"),
        signature_algorithm=cert.get("signature_algorithm"),
        chain_valid=cert.get("chain_valid"),
        san=cert.get("san", []),
    )


# ---- unified domain investigation ----------------------------------------- #
@router.get("/{domain}", response_model=DomainResult)
async def investigate_domain(
    domain: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    domain = _normalize(domain)
    t0 = time.perf_counter()

    # ---- run legacy + new providers concurrently ---- #
    orch = get_orchestrator()
    dns_provider = orch.providers.get("dns")
    whois_provider = orch.providers.get("whois")
    vt_provider = orch.providers.get("virustotal")
    crtsh_provider = orch.providers.get("crtsh")

    import asyncio
    legacy_dns = _legacy_dns(domain)
    legacy_whois_task = _legacy_whois_async(domain)
    legacy_ssl = _legacy_ssl(domain)
    legacy_techs_task = detect_tech(f"https://{domain}")

    provider_tasks = []
    if dns_provider and dns_provider.enabled:
        provider_tasks.append(("dns", dns_provider.run(domain)))
    if whois_provider and whois_provider.enabled:
        provider_tasks.append(("whois", whois_provider.run(domain)))
    if vt_provider and vt_provider.enabled:
        provider_tasks.append(("virustotal", vt_provider.run(domain, kind="domain")))
    if crtsh_provider and crtsh_provider.enabled:
        provider_tasks.append(("crtsh", crtsh_provider.run(domain)))

    # Headers (still needed for CDN/hosting detection)
    async def _headers():
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
                follow_redirects=True,
                headers={"User-Agent": "HelloYou/1.0 (+educational)"},
            ) as c:
                r = await c.get(f"https://{domain}")
                return dict(r.headers)
        except Exception:
            return {}

    legacy_techs, legacy_whois, headers, provider_results = await asyncio.gather(
        legacy_techs_task, legacy_whois_task, _headers(),
        asyncio.gather(*[t for _, t in provider_tasks], return_exceptions=True),
    )

    # ---- aggregate ---- #
    providers_dict: dict = {}
    for (name, _), res in zip(provider_tasks, provider_results):
        providers_dict[name] = res.to_dict() if hasattr(res, "to_dict") else {"ok": False, "error": str(res)}

    technologies = [Technology(**t) for t in legacy_techs]

    cdn = None
    hosting = None
    server = headers.get("server", "") or ""
    if "cloudflare" in server.lower() or "cf-ray" in {k.lower() for k in headers}:
        cdn = "Cloudflare"
    elif "akamai" in server.lower():
        cdn = "Akamai"
    elif "vercel" in server.lower():
        cdn = "Vercel"
    hosting = server or None

    # risk score (legacy heuristic, enriched with VT)
    parts: list[int] = []
    if legacy_ssl is None:
        parts.append(30)
    elif legacy_ssl.days_remaining is not None and legacy_ssl.days_remaining < 14:
        parts.append(40)
    if not legacy_dns.dnssec:
        parts.append(15)
    if not legacy_dns.mx:
        parts.append(10)
    vt_data = providers_dict.get("virustotal", {}).get("data") or {}
    if isinstance(vt_data.get("score"), (int, float)):
        parts.append(int(vt_data["score"]))
    from app.osint.risk import aggregate, level
    risk = aggregate(parts)
    duration_ms = int((time.perf_counter() - t0) * 1000)

    result = {
        "domain": domain,
        "dns": legacy_dns.model_dump(mode="json"),
        "ssl": legacy_ssl.model_dump(mode="json") if legacy_ssl else None,
        "whois": legacy_whois.model_dump(mode="json") if legacy_whois else None,
        "technologies": [t.model_dump() for t in technologies],
        "headers": headers,
        "cdn": cdn,
        "hosting": hosting,
        "risk_score": risk,
        "threat_level": level(risk),
    }
    # Store the new provider data alongside (non-breaking)
    result["providers"] = to_jsonable(providers_dict)
    await save_investigation(
        db, user.id, kind="domain", target=domain, result=result,
        risk_score=risk, duration_ms=duration_ms,
    )
    # Return only legacy fields
    return DomainResult(**{k: v for k, v in result.items() if k != "providers"})


# ---- DNS ----------------------------------------------------------------- #
dns_router = APIRouter(prefix="/dns", tags=["dns"])


@dns_router.get("/{domain}", response_model=DNSRecords)
async def dns_lookup(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    return _legacy_dns(domain)


# ---- WHOIS --------------------------------------------------------------- #
whois_router = APIRouter(prefix="/whois", tags=["whois"])


@whois_router.get("/{domain}", response_model=WHOISInfo)
async def whois_lookup(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    w = await _legacy_whois_async(domain)
    if not w:
        raise HTTPException(404, "No RDAP endpoint found for this TLD")
    return w


# ---- SSL ----------------------------------------------------------------- #
ssl_router = APIRouter(prefix="/ssl", tags=["ssl"])


@ssl_router.get("/{domain}", response_model=SSLInfo)
async def ssl_lookup(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    s = _legacy_ssl(domain)
    if not s:
        raise HTTPException(404, "Could not retrieve certificate")
    return s


# ---- Certificate Transparency -------------------------------------------- #
ct_router = APIRouter(prefix="/ct", tags=["certificate-transparency"])


@ct_router.get("/{domain}")
async def ct_lookup(domain: str, user: CurrentUser, limit: int = Query(50, ge=1, le=500)):
    domain = _normalize(domain)
    orch = get_orchestrator()
    crtsh = orch.providers.get("crtsh")
    if crtsh and crtsh.enabled:
        pr = await crtsh.run(domain, limit=limit)
        if pr.ok:
            return pr.data.get("certificates", [])
    # Fallback to legacy
    from app.osint.ct_provider import search_certificates
    return await search_certificates(domain, limit=limit)


# ---- Subdomain Discovery ------------------------------------------------- #
sub_router = APIRouter(prefix="/subdomains", tags=["subdomain-discovery"])


@sub_router.get("/{domain}", response_model=SubdomainResult)
async def subdomain_discovery(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    orch = get_orchestrator()
    crtsh = orch.providers.get("crtsh")
    if crtsh and crtsh.enabled:
        pr = await crtsh.run(domain)
        if pr.ok:
            subs = pr.data.get("subdomains", [])
            return SubdomainResult(domain=domain, subdomains=subs, sources=["crt.sh"])
    from app.osint.ct_provider import discover_subdomains
    subs = await discover_subdomains(domain)
    return SubdomainResult(domain=domain, subdomains=subs, sources=["crt.sh"])


# ---- Technology Detection ----------------------------------------------- #
tech_router = APIRouter(prefix="/tech", tags=["technology-detection"])


@tech_router.get("/{domain}", response_model=list[Technology])
async def technology_detection(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    url = f"https://{domain}" if not domain.startswith(("http://", "https://")) else domain
    techs = await detect_tech(url)
    return [Technology(**t) for t in techs]
