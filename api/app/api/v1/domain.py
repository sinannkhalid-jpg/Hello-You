"""Domain / DNS / WHOIS / SSL / Subdomain / Technology routers."""
from __future__ import annotations

import time
from typing import Annotated

import httpx
import tldextract  # type: ignore
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.ct_provider import discover_subdomains, search_certificates
from app.osint.dns_provider import (
    dnssec_ok,
    lookup_a,
    lookup_aaaa,
    lookup_caa,
    lookup_mx,
    lookup_ns,
    lookup_ptr,
    lookup_soa,
    lookup_txt,
)
from app.osint.http import get_json
from app.osint.risk import aggregate, level
from app.osint.ssl_provider import get_cert
from app.osint.tech_provider import detect as detect_tech
from app.osint.whois_provider import rdap_lookup, summarize_rdap
from app.schemas.osint import (
    DNSRecords,
    DomainResult,
    SSLInfo,
    SubdomainResult,
    Technology,
    WHOISInfo,
)
from app.services.investigation_service import save_investigation

router = APIRouter(prefix="/domain", tags=["domain"])


def _normalize(domain: str) -> str:
    domain = domain.strip().lower()
    if domain.startswith(("http://", "https://")):
        domain = domain.split("://", 1)[1]
    domain = domain.split("/", 1)[0]
    if not domain or "." not in domain:
        raise HTTPException(400, "Invalid domain")
    return domain


@router.get("/{domain}", response_model=DomainResult)
async def investigate_domain(
    domain: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    domain = _normalize(domain)
    t0 = time.perf_counter()
    dns = DNSRecords(
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
    cert = get_cert(domain)
    ssl: SSLInfo | None = None
    if cert:
        from datetime import datetime
        ssl = SSLInfo(
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
    rdap = await rdap_lookup(domain)
    whois: WHOISInfo | None = None
    if rdap:
        whois = WHOISInfo(**summarize_rdap(rdap))

    techs_raw = await detect_tech(domain)
    technologies = [Technology(**t) for t in techs_raw]

    # Fetch response headers for a few days.
    headers: dict[str, str] = {}
    cdn = None
    hosting = None
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
            follow_redirects=True,
            headers={"User-Agent": "OSINT-Nexus/1.0 (+educational)"},
        ) as c:
            r = await c.get(f"https://{domain}")
            for k, v in r.headers.items():
                headers[k] = v
            server = r.headers.get("server", "")
            if "cloudflare" in server.lower() or "cf-ray" in {k.lower() for k in r.headers}:
                cdn = "Cloudflare"
            elif "akamai" in server.lower():
                cdn = "Akamai"
            elif "vercel" in server.lower():
                cdn = "Vercel"
            hosting = server or None
    except Exception:
        pass

    parts: list[int] = []
    if ssl is None:
        parts.append(30)
    elif ssl.days_remaining is not None and ssl.days_remaining < 14:
        parts.append(40)
    if not dns.dnssec:
        parts.append(15)
    if not dns.mx:
        parts.append(10)
    risk = aggregate(parts)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    result = {
        "domain": domain,
        "dns": dns.model_dump(mode="json"),
        "ssl": ssl.model_dump(mode="json") if ssl else None,
        "whois": whois.model_dump(mode="json") if whois else None,
        "technologies": [t.model_dump() for t in technologies],
        "headers": headers,
        "cdn": cdn,
        "hosting": hosting,
        "risk_score": risk,
        "threat_level": level(risk),
    }
    await save_investigation(
        db, user.id, kind="domain", target=domain, result=result,
        risk_score=risk, duration_ms=duration_ms,
    )
    return DomainResult(**result)


dns_router = APIRouter(prefix="/dns", tags=["dns"])


@dns_router.get("/{domain}", response_model=DNSRecords)
async def dns_lookup(domain: str, user: CurrentUser):
    domain = _normalize(domain)
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


whois_router = APIRouter(prefix="/whois", tags=["whois"])


@whois_router.get("/{domain}", response_model=WHOISInfo)
async def whois_lookup(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    rdap = await rdap_lookup(domain)
    if not rdap:
        raise HTTPException(404, "No RDAP endpoint found for this TLD")
    return WHOISInfo(**summarize_rdap(rdap))


ssl_router = APIRouter(prefix="/ssl", tags=["ssl"])


@ssl_router.get("/{domain}", response_model=SSLInfo)
async def ssl_lookup(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    cert = get_cert(domain)
    if not cert:
        raise HTTPException(404, "Could not retrieve certificate")
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


ct_router = APIRouter(prefix="/ct", tags=["certificate-transparency"])


@ct_router.get("/{domain}")
async def ct_lookup(domain: str, user: CurrentUser, limit: int = Query(50, ge=1, le=500)):
    domain = _normalize(domain)
    return await search_certificates(domain, limit=limit)


sub_router = APIRouter(prefix="/subdomains", tags=["subdomain-discovery"])


@sub_router.get("/{domain}", response_model=SubdomainResult)
async def subdomain_discovery(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    subs = await discover_subdomains(domain)
    return SubdomainResult(domain=domain, subdomains=subs, sources=["crt.sh"])


tech_router = APIRouter(prefix="/tech", tags=["technology-detection"])


@tech_router.get("/{domain}", response_model=list[Technology])
async def technology_detection(domain: str, user: CurrentUser):
    domain = _normalize(domain)
    if not domain.startswith(("http://", "https://")):
        url = f"https://{domain}"
    else:
        url = domain
    techs = await detect_tech(url)
    return [Technology(**t) for t in techs]
