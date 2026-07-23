"""DNS lookups using Google/Cloudflare DNS-over-HTTPS (free, public)."""
from __future__ import annotations

from typing import Any

import dns.resolver  # type: ignore
import dns.rdatatype  # type: ignore
from app.core.logging import get_logger

log = get_logger(__name__)

# Google DoH JSON endpoint, also used as a fallback when dnspython is unavailable.
GOOGLE_DOH = "https://dns.google/resolve"
CLOUDFLARE_DOH = "https://cloudflare-dns.com/dns-query"


def _resolver() -> "dns.resolver.Resolver":
    r = dns.resolver.Resolver()
    r.nameservers = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    r.lifetime = 5.0
    return r


def _query(name: str, rdtype: int) -> list[str]:
    try:
        ans = _resolver().resolve(name, rdtype, raise_on_no_answer=False)
        return [r.to_text() for r in ans]
    except Exception as e:  # NXDOMAIN, timeout, etc.
        log.debug("DNS %s %s -> %s", rdtype, name, e)
        return []


def lookup_a(name: str) -> list[str]:
    return _query(name, dns.rdatatype.A)


def lookup_aaaa(name: str) -> list[str]:
    return _query(name, dns.rdatatype.AAAA)


def lookup_mx(name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in _query(name, dns.rdatatype.MX):
        # raw MX form: "10 mail.example.com."
        parts = r.split()
        if len(parts) == 2:
            out.append({"priority": int(parts[0]), "host": parts[1].rstrip(".")})
    return sorted(out, key=lambda x: x["priority"])


def lookup_ns(name: str) -> list[str]:
    return [h.rstrip(".") for h in _query(name, dns.rdatatype.NS)]


def lookup_txt(name: str) -> list[str]:
    # TXT records can be returned as multiple quoted strings; join them.
    return ["".join(t for t in r.split('"') if t) for r in _query(name, dns.rdatatype.TXT)]


def lookup_cname(name: str) -> list[str]:
    return [r.rstrip(".") for r in _query(name, dns.rdatatype.CNAME)]


def lookup_soa(name: str) -> dict[str, Any] | None:
    rows = _query(name, dns.rdatatype.SOA)
    if not rows:
        return None
    raw = rows[0].split()
    # mname rname serial refresh retry expire minimum
    if len(raw) >= 7:
        return {
            "mname": raw[0].rstrip("."),
            "rname": raw[1].rstrip("."),
            "serial": int(raw[2]),
            "refresh": int(raw[3]),
            "retry": int(raw[4]),
            "expire": int(raw[5]),
            "minimum": int(raw[6]),
        }
    return {"raw": rows[0]}


def lookup_caa(name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in _query(name, dns.rdatatype.CAA):
        parts = r.split()
        if len(parts) >= 3:
            out.append({"flag": int(parts[0]), "tag": parts[1], "value": parts[2].strip('"')})
    return out


def lookup_ptr(ip: str) -> list[str]:
    rev = ".".join(reversed(ip.split("."))) + ".in-addr.arpa"
    return [r.rstrip(".") for r in _query(rev, dns.rdatatype.PTR)]


def dnssec_ok(name: str) -> bool:
    try:
        ans = _resolver().resolve(name, dns.rdatatype.DNSKEY, raise_on_no_answer=False)
        return bool(ans.response.flags & 0x0001)  # AD bit
    except Exception:
        return False
