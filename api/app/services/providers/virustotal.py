"""
VirusTotal provider.

Free public API: 4 requests/minute, 500/day.
Docs: https://docs.virustotal.com/reference/overview

We support domain, IP, and file-hash lookups. Each lookup pulls the
`last_analysis_stats` block which is the normalized reputation signal.
"""
from __future__ import annotations

from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json
from app.services.providers.types import normalize_reputation


class VirusTotalProvider(BaseProvider):
    name = "virustotal"
    kind = "domain"
    enabled = True
    requires_key = True
    api_key_env = "VIRUSTOTAL_API_KEY"
    rate_limit_per_minute = 4
    cache_ttl = 60 * 60 * 6
    timeout_seconds = 12.0
    health_url = "https://www.virustotal.com/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        kind = kwargs.get("kind") or self._infer_kind(target)
        if kind == "ip":
            return await self._ip_report(target)
        if kind == "url":
            return await self._url_report(target)
        if kind == "hash":
            return await self._hash_report(target)
        return await self._domain_report(target)

    @staticmethod
    def _infer_kind(target: str) -> str:
        if all(p.isdigit() for p in target.split(".")) and target.count(".") == 3:
            return "ip"
        if target.startswith("http://") or target.startswith("https://"):
            return "url"
        if len(target) in (32, 40, 64) and all(c in "0123456789abcdefABCDEF" for c in target):
            return "hash"
        return "domain"

    async def _domain_report(self, domain: str) -> dict[str, Any]:
        return await self._vt_lookup(f"https://www.virustotal.com/api/v3/domains/{domain}", "domain")

    async def _ip_report(self, ip: str) -> dict[str, Any]:
        return await self._vt_lookup(f"https://www.virustotal.com/api/v3/ip_addresses/{ip}", "ip")

    async def _hash_report(self, h: str) -> dict[str, Any]:
        return await self._vt_lookup(f"https://www.virustotal.com/api/v3/files/{h}", "hash")

    async def _url_report(self, url: str) -> dict[str, Any]:
        # URL lookups require a separate /urls POST to get an id — out of
        # scope for this version.
        return self._empty("url", "URL lookups require the /api/v3/urls endpoint (not exposed)")

    async def _vt_lookup(self, url: str, kind: str) -> dict[str, Any]:
        data = await get_json(url, headers={"x-apikey": self.api_key or ""})
        if not data or not isinstance(data, dict):
            return self._empty(kind, "no data")
        attrs = (data.get("data") or {}).get("attributes") or {}
        stats = attrs.get("last_analysis_stats") or {}
        rep = normalize_reputation(
            malicious=stats.get("malicious", 0),
            suspicious=stats.get("suspicious", 0),
            harmless=stats.get("harmless", 0),
            undetected=stats.get("undetected", 0),
            extra={
                "reputation": attrs.get("reputation"),
                "categories": attrs.get("categories", {}),
                "registrar": attrs.get("registrar"),
                "creation_date": attrs.get("creation_date"),
                "asn": attrs.get("asn"),
                "as_owner": attrs.get("as_owner"),
                "country": attrs.get("country"),
                "last_modification_date": attrs.get("last_modification_date"),
                "tags": attrs.get("tags", []),
            },
        )
        return {
            "found": True,
            "kind": kind,
            "score": rep["score"],
            "threat_level": rep["threat_level"],
            "malicious": rep["malicious"],
            "suspicious": rep["suspicious"],
            "harmless": rep["harmless"],
            "undetected": rep["undetected"],
            "extra": rep.get("extra", {}),
        }

    @staticmethod
    def _empty(kind: str, reason: str) -> dict[str, Any]:
        return {
            "found": False,
            "kind": kind,
            "score": 0,
            "threat_level": "unknown",
            "malicious": 0,
            "suspicious": 0,
            "harmless": 0,
            "undetected": 0,
            "extra": {"reason": reason},
        }


PROVIDER_CLASS = VirusTotalProvider
