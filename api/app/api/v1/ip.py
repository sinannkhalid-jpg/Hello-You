"""IP investigation router.

Port scanning is intentionally NOT performed by default. The `/port-scan`
endpoint requires an explicit `authorized: true` confirmation in the body,
and the target must be a public IP. We never scan localhost or private
ranges, and we never bypass anything — these are plain TCP connect() probes
to common ports on systems you have permission to test.
"""
from __future__ import annotations

import asyncio
import ipaddress
import time
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.osint.ip_provider import geolocate, threat_intel
from app.osint.risk import aggregate, level
from app.schemas.osint import IPResult
from app.services.investigation_service import save_investigation

router = APIRouter(prefix="/ip", tags=["ip"])

# Conservative set of common ports, scanned only on explicit request + confirmation.
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 3306, 3389, 5432, 6379, 8080, 8443]


def _validate_public_ip(ip: str) -> str:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(400, "Invalid IP")
    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast:
        raise HTTPException(400, "Refusing to scan non-public IPs")
    return str(addr)


async def _scan_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def _do_ip(
    ip: str, user, db: AsyncSession, *, scan_ports: bool, authorized: bool
) -> IPResult:
    ip = _validate_public_ip(ip)
    t0 = time.perf_counter()
    info = await geolocate(ip)
    intel = await threat_intel(ip)
    open_ports: list[int] = []
    if scan_ports:
        if not authorized:
            raise HTTPException(
                403,
                "Port scanning requires explicit `authorized: true`. "
                "Only scan systems you own or have written permission to test.",
            )
        results = await asyncio.gather(*[_scan_port(ip, p) for p in COMMON_PORTS])
        open_ports = [p for p, ok in zip(COMMON_PORTS, results) if ok]

    abuse = None
    abuse_data = intel.get("abuseipdb") or {}
    if isinstance(abuse_data, dict):
        d = abuse_data.get("data") or {}
        abuse = d.get("totalReports")

    parts = []
    if open_ports:
        parts.append(min(20 + len(open_ports) * 5, 70))
    if abuse and abuse > 5:
        parts.append(min(20 + abuse, 90))
    risk = aggregate(parts)
    duration_ms = int((time.perf_counter() - t0) * 1000)
    result = {
        "ip": ip,
        "reverse_dns": info.get("reverse_dns"),
        "geo": info.get("geo") or {},
        "isp": info.get("isp"),
        "asn": info.get("asn"),
        "asn_org": info.get("asn_org"),
        "open_ports": open_ports,
        "threat_intel": intel,
        "abuse_reports": abuse,
        "risk_score": risk,
        "threat_level": level(risk),
    }
    await save_investigation(
        db, user.id, kind="ip", target=ip, result=result, risk_score=risk, duration_ms=duration_ms
    )
    return IPResult(**result)


@router.get("/{ip}", response_model=IPResult)
async def investigate_ip(
    ip: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await _do_ip(ip, user, db, scan_ports=False, authorized=False)


@router.post("/{ip}/port-scan", response_model=IPResult)
async def port_scan(
    ip: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorized: bool = Body(..., embed=True),
):
    return await _do_ip(ip, user, db, scan_ports=True, authorized=authorized)
