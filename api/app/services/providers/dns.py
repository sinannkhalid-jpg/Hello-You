"""
DNS provider.

Wraps the existing dnspython-based implementation but returns a
normalized, cache-friendly dict.
"""
from __future__ import annotations

from typing import Any

import dns.rdatatype  # type: ignore

from app.services.providers.base import BaseProvider
from app.osint.dns_provider import (  # type: ignore  # reuse proven impl
    lookup_a, lookup_aaaa, lookup_caa, lookup_mx, lookup_ns,
    lookup_ptr, lookup_soa, lookup_txt, dnssec_ok,
)


class DNSProvider(BaseProvider):
    name = "dns"
    kind = "domain"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 120
    cache_ttl = 60 * 5  # 5 min
    timeout_seconds = 8.0
    health_url = "https://1.1.1.1/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        # dnspython is sync; run it in a thread to avoid blocking the loop.
        import asyncio
        loop = asyncio.get_running_loop()

        async def _q(name: str, rdtype: int) -> list[str]:
            return await loop.run_in_executor(None, _sync, name, rdtype)

        def _sync(name: str, rdtype: int) -> list[str]:
            try:
                if rdtype == dns.rdatatype.A: return lookup_a(name)
                if rdtype == dns.rdatatype.AAAA: return lookup_aaaa(name)
                if rdtype == dns.rdatatype.MX: return [f"{m['priority']} {m['host']}" for m in lookup_mx(name)]
                if rdtype == dns.rdatatype.NS: return lookup_ns(name)
                if rdtype == dns.rdatatype.TXT: return lookup_txt(name)
                if rdtype == dns.rdatatype.SOA: return [str(lookup_soa(name))]
                if rdtype == dns.rdatatype.CAA: return [f"{c['flag']} {c['tag']} {c['value']}" for c in lookup_caa(name)]
                if rdtype == dns.rdatatype.PTR: return lookup_ptr(name)
            except Exception:
                return []
            return []

        # We only run this for IP-shaped targets in the PTR branch.
        is_ip = all(p.isdigit() for p in target.split(".")) and target.count(".") == 3

        a, aaaa, mx, ns, txt, soa, caa, dnssec = await asyncio.gather(
            _q(target, dns.rdatatype.A),
            _q(target, dns.rdatatype.AAAA),
            _q(target, dns.rdatatype.MX),
            _q(target, dns.rdatatype.NS),
            _q(target, dns.rdatatype.TXT),
            _q(target, dns.rdatatype.SOA),
            _q(target, dns.rdatatype.CAA),
            loop.run_in_executor(None, dnssec_ok, target),
        )
        ptr = await _q(target, dns.rdatatype.PTR) if is_ip else []
        return {
            "a": a,
            "aaaa": aaaa,
            "mx": mx,
            "ns": ns,
            "txt": txt,
            "soa": soa[0] if soa else None,
            "caa": caa,
            "ptr": ptr,
            "dnssec": bool(dnssec),
        }
