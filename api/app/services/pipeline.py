"""
Investigation pipeline.

Composes the orchestrator's per-provider results into the final
investigation response:

  • confidence     — aggregate confidence 0..1
  • evidence[]     — findings tagged with severity (Critical/High/Medium/Low/Info)
  • timeline[]     — ordered event log of what happened during the run
  • graph          — nodes + edges for React Flow visualization
  • progress       — full list of progress events (also streamed via SSE)
  • meta           — duration, provider counts, etc.

The pipeline is fully async. All provider calls run concurrently via
`asyncio.gather()`.

Backwards compatibility: when `legacy_fields=True` the result also
contains the legacy flat `summary` dict and the per-provider `providers`
map so existing frontend pages keep working without changes.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterable, Sequence

from app.core.logging import get_logger
from app.services.orchestrator import get_orchestrator
from app.services.providers.base import ProviderResult

log = get_logger("pipeline")


# --------------------------------------------------------------------------- #
# Evidence severity levels (requirement #8)
# --------------------------------------------------------------------------- #
SEVERITY_LEVELS: tuple[str, ...] = ("critical", "high", "medium", "low", "info")
SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(SEVERITY_LEVELS)}


def severity_from_score(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    if score > 0:
        return "low"
    return "info"


# --------------------------------------------------------------------------- #
# Progress event types
# --------------------------------------------------------------------------- #
class ProgressEvent:
    """A single progress event in the investigation stream."""

    __slots__ = ("stage", "message", "provider", "ts", "meta")

    def __init__(
        self,
        stage: str,
        message: str,
        provider: str | None = None,
        meta: dict[str, Any] | None = None,
    ):
        self.stage = stage
        self.message = message
        self.provider = provider
        self.ts = time.time()
        self.meta = meta or {}

    def to_dict(self) -> dict[str, Any]:
        d = {"stage": self.stage, "message": self.message, "ts": self.ts}
        if self.provider:
            d["provider"] = self.provider
        if self.meta:
            d["meta"] = self.meta
        return d


# --------------------------------------------------------------------------- #
# Pipeline runner
# --------------------------------------------------------------------------- #
class InvestigationPipeline:
    """Runs a full investigation end-to-end and produces the final response."""

    def __init__(self) -> None:
        self.orchestrator = get_orchestrator()
        self.events: list[ProgressEvent] = []

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def run(
        self,
        kind: str,
        target: str,
        *,
        providers: list[str] | None = None,
        include_graph: bool = True,
        include_timeline: bool = True,
        legacy_fields: bool = True,
    ) -> dict[str, Any]:
        """Run the full investigation pipeline.

        Returns the final response dict (see module docstring for shape).
        """
        t0 = time.perf_counter()
        self.events = []

        self._emit("start", f"Starting investigation of {kind} '{target}'",
                   meta={"kind": kind, "target": target})

        # 1. Plan: pick providers
        selected = self.orchestrator._select_providers(kind, providers)
        for prov in selected:
            self._emit(
                "checking",
                f"Checking {prov.name}…",
                provider=prov.name,
            )
        skipped = [
            name for name, p in self.orchestrator.providers.items()
            if name not in [s.name for s in selected]
            and p.kind == kind
        ]
        for s in skipped:
            self._emit(
                "skipped",
                f"Skipping {s} (disabled or no key)",
                provider=s,
            )

        # 2. Run all providers concurrently
        tasks = [prov.run(target) for prov in selected]
        results: list[ProviderResult] = await asyncio.gather(
            *tasks, return_exceptions=False,
        )
        for r in results:
            if r.ok:
                self._emit(
                    "completed",
                    f"Completed {r.source} in {r.duration_ms}ms",
                    provider=r.source,
                    meta={"duration_ms": r.duration_ms, "cached": r.cached},
                )
            else:
                self._emit(
                    "failed",
                    f"Failed {r.source}: {r.error}",
                    provider=r.source,
                    meta={"error": r.error},
                )

        # 3. Build canonical envelopes
        by_source: dict[str, dict[str, Any]] = {}
        for r in results:
            by_source[r.source] = r.to_dict()

        # 4. Final confidence (0..1) — average of per-provider confidences
        conf_values = [
            r.to_dict()["confidence"]
            for r in results
            if r.ok
        ]
        final_confidence = (
            round(sum(conf_values) / len(conf_values), 2) if conf_values else 0.0
        )

        # 5. Evidence with severity
        evidence = self._build_evidence(results)

        # 6. Timeline
        timeline = self._build_timeline(results) if include_timeline else []

        # 7. Relationship graph
        graph = (
            self._build_graph(kind, target, results) if include_graph
            else {"nodes": [], "edges": []}
        )

        # 8. Summary
        ok_count = sum(1 for r in results if r.ok)
        fail_count = len(results) - ok_count
        elapsed = int((time.perf_counter() - t0) * 1000)
        summary = self._build_summary(results, final_confidence, ok_count, fail_count)

        self._emit("done", f"Investigation completed in {elapsed}ms",
                   meta={"duration_ms": elapsed, "confidence": final_confidence})

        response: dict[str, Any] = {
            "target": target,
            "kind": kind,
            "providers": by_source,
            "evidence": evidence,
            "graph": graph,
            "timeline": timeline,
            "progress": [e.to_dict() for e in self.events],
            "summary": summary,
            "confidence": final_confidence,
            "meta": {
                "duration_ms": elapsed,
                "providers_queried": len(results),
                "providers_ok": ok_count,
                "providers_failed": fail_count,
                "providers_skipped": len(skipped),
            },
        }
        if legacy_fields:
            # Already includes "summary" and "providers"; nothing else needed
            pass
        return response

    async def stream(
        self,
        kind: str,
        target: str,
        *,
        providers: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield progress events as the investigation runs, then the final result.

        Used by the SSE endpoint.
        """
        # Run in background while we yield events
        task = asyncio.create_task(
            self.run(kind, target, providers=providers)
        )
        last_idx = 0
        while not task.done():
            await asyncio.sleep(0.05)
            for ev in self.events[last_idx:]:
                yield ev.to_dict()
                last_idx += 1
        # Drain remaining
        for ev in self.events[last_idx:]:
            yield ev.to_dict()
        result = await task
        yield {"stage": "result", "result": result}

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _emit(self, stage: str, message: str, *, provider: str | None = None,
              meta: dict[str, Any] | None = None) -> ProgressEvent:
        ev = ProgressEvent(stage, message, provider, meta)
        self.events.append(ev)
        return ev

    def _build_evidence(self, results: list[ProviderResult]) -> list[dict[str, Any]]:
        """Convert provider results into severity-tagged evidence items."""
        out: list[dict[str, Any]] = []
        for r in results:
            d = r.to_dict()
            if not d.get("ok"):
                # Failed provider — info-level evidence about the failure
                out.append({
                    "id": f"{r.source}-error",
                    "provider": r.source,
                    "severity": "info",
                    "title": f"{r.source} unavailable",
                    "description": d.get("error") or "no data",
                    "confidence": 0.0,
                })
                continue

            score = int(d.get("data", {}).get("score", 0) or 0)
            sev = severity_from_score(score)

            # Provider-specific finding titles
            if r.source == "shodan":
                ports = d["data"].get("ports", [])
                vulns = d["data"].get("vulns", [])
                if vulns:
                    out.append({
                        "id": f"{r.source}-vulns",
                        "provider": r.source,
                        "severity": "critical" if vulns else "high",
                        "title": f"Shodan reports {len(vulns)} known CVEs",
                        "description": ", ".join(vulns[:5]),
                        "confidence": d.get("confidence", 0.5),
                    })
                if ports:
                    out.append({
                        "id": f"{r.source}-ports",
                        "provider": r.source,
                        "severity": "medium" if len(ports) > 5 else "low",
                        "title": f"{len(ports)} open ports observed",
                        "description": ", ".join(map(str, ports[:20])),
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "abuseipdb":
                conf = d["data"].get("abuse_confidence", 0)
                reports = d["data"].get("total_reports", 0)
                if reports > 0:
                    out.append({
                        "id": f"{r.source}-abuse",
                        "provider": r.source,
                        "severity": severity_from_score(conf),
                        "title": f"AbuseIPDB confidence: {conf}%",
                        "description": f"{reports} report(s) on file",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "virustotal":
                mal = d["data"].get("malicious", 0)
                if mal:
                    out.append({
                        "id": f"{r.source}-malicious",
                        "provider": r.source,
                        "severity": "critical" if mal > 5 else "high",
                        "title": f"VirusTotal: {mal} engines flagged this",
                        "description": "See the full report for vendor details.",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "username":
                count = d["data"].get("count", 0)
                if count:
                    out.append({
                        "id": f"{r.source}-profiles",
                        "provider": r.source,
                        "severity": "info",
                        "title": f"Username present on {count} public platform(s)",
                        "description": f"Checked {d['data'].get('total_checked', 0)} platforms.",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "hibp":
                n = len(d["data"].get("breaches", []) or [])
                if n:
                    out.append({
                        "id": f"{r.source}-breaches",
                        "provider": r.source,
                        "severity": "critical" if n > 5 else "high",
                        "title": f"Email appears in {n} breach(es)",
                        "description": "Use HIBP for full breach names.",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "leakcheck":
                if d["data"].get("found"):
                    out.append({
                        "id": f"{r.source}-leaks",
                        "provider": r.source,
                        "severity": "high",
                        "title": "LeakCheck reports exposures",
                        "description": f"{len(d['data'].get('sources', []))} source(s).",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "gravatar":
                if d["data"].get("found"):
                    out.append({
                        "id": f"{r.source}-profile",
                        "provider": r.source,
                        "severity": "info",
                        "title": "Public Gravatar profile found",
                        "description": d["data"].get("display_name") or "",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "ipapi":
                geo = d["data"].get("geo", {})
                if geo.get("country"):
                    out.append({
                        "id": f"{r.source}-geo",
                        "provider": r.source,
                        "severity": "info",
                        "title": f"IP geolocated to {geo.get('city')}, {geo.get('country')}",
                        "description": f"ISP: {d['data'].get('isp') or 'unknown'}",
                        "confidence": d.get("confidence", 0.5),
                    })
            elif r.source == "dns":
                if d["data"].get("dnssec"):
                    out.append({
                        "id": f"{r.source}-dnssec",
                        "provider": r.source,
                        "severity": "info",
                        "title": "DNSSEC is enabled",
                        "description": "Domain is signed.",
                        "confidence": d.get("confidence", 0.5),
                    })
                elif d["data"].get("a") and not d["data"].get("mx"):
                    out.append({
                        "id": f"{r.source}-no-mx",
                        "provider": r.source,
                        "severity": "low",
                        "title": "No MX records — domain cannot receive email",
                        "description": "",
                        "confidence": d.get("confidence", 0.5),
                    })
            else:
                # Generic: emit a low-severity evidence item per provider
                if score > 0:
                    out.append({
                        "id": f"{r.source}-signal",
                        "provider": r.source,
                        "severity": sev,
                        "title": f"{r.source} signal",
                        "description": f"Score: {score}/100",
                        "confidence": d.get("confidence", 0.5),
                    })
        # Sort: critical first, then high, medium, low, info
        out.sort(key=lambda e: (SEVERITY_RANK.get(e["severity"], 99), -e.get("confidence", 0)))
        return out

    def _build_timeline(self, results: list[ProviderResult]) -> list[dict[str, Any]]:
        """Ordered list of investigation events for the timeline UI."""
        timeline: list[dict[str, Any]] = []
        timeline.append({
            "ts": self.events[0].ts if self.events else time.time(),
            "stage": "start",
            "label": "Investigation started",
            "kind": "info",
        })
        # Group by severity
        for r in sorted(results, key=lambda x: (x.to_dict()["confidence"]), reverse=True):
            d = r.to_dict()
            timeline.append({
                "ts": time.time() - (len(timeline) * 0.01),  # synthetic order
                "stage": d.get("provider", "?"),
                "label": (
                    f"{d['provider']}: completed in {d['response_time_ms']}ms"
                    if d.get("ok")
                    else f"{d['provider']}: failed ({d.get('error')})"
                ),
                "kind": "ok" if d.get("ok") else "error",
            })
        timeline.append({
            "ts": time.time(),
            "stage": "done",
            "label": "Investigation completed",
            "kind": "info",
        })
        return timeline

    def _build_graph(
        self,
        kind: str,
        target: str,
        results: list[ProviderResult],
    ) -> dict[str, Any]:
        """Build a relationship graph (nodes + edges) for React Flow.

        Mirrors the logic in `app/api/v1/graph.py` so existing frontend
        code can consume it directly.
        """
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        def add_node(nid: str, label: str, ntype: str, data: dict | None = None) -> str:
            if nid not in nodes:
                nodes[nid] = {
                    "id": nid, "label": label, "type": ntype, "data": data or {}
                }
            return nid

        root = add_node(f"{kind}:{target}", str(target), kind, {"root": True})

        for r in results:
            d = r.to_dict()
            data = d.get("data") or {}
            if r.source == "dns":
                for ip in (data.get("a") or []):
                    nid = add_node(f"ip:{ip}", ip, "ip")
                    edges.append({"source": root, "target": nid, "label": "A"})
                for mx in (data.get("mx") or []):
                    host = mx.get("host") if isinstance(mx, dict) else None
                    if host:
                        nid = add_node(f"domain:{host}", host, "domain")
                        edges.append({"source": root, "target": nid, "label": f"MX {mx.get('priority')}"})
                for ns in (data.get("ns") or []):
                    nid = add_node(f"domain:{ns}", ns, "domain")
                    edges.append({"source": root, "target": nid, "label": "NS"})
            elif r.source == "whois":
                w = data.get("whois") or data
                for ns in (w.get("nameservers") or []):
                    if isinstance(ns, str):
                        nid = add_node(f"domain:{ns}", ns, "domain")
                        edges.append({"source": root, "target": nid, "label": "NS"})
                reg = w.get("registrar")
                if reg:
                    nid = add_node(f"company:{reg}", reg, "company")
                    edges.append({"source": root, "target": nid, "label": "registrar"})
            elif r.source == "ipapi":
                geo = data.get("geo") or {}
                if geo.get("country"):
                    nid = add_node(f"country:{geo['country']}", geo["country"], "company",
                                   data={"lat": geo.get("latitude"), "lng": geo.get("longitude")})
                    edges.append({"source": root, "target": nid, "label": "located in"})
                if data.get("isp"):
                    nid = add_node(f"company:{data['isp']}", data["isp"], "company")
                    edges.append({"source": root, "target": nid, "label": "ISP"})
            elif r.source == "abuseipdb":
                if data.get("total_reports", 0) > 0:
                    nid = add_node(f"company:AbuseIPDB", "AbuseIPDB", "company")
                    edges.append({"source": root, "target": nid, "label": "reported"})
            elif r.source == "shodan":
                for p in (data.get("ports") or [])[:20]:
                    nid = add_node(f"port:{target}:{p}", f":{p}", "ip")
                    edges.append({"source": root, "target": nid, "label": "open"})
            elif r.source == "virustotal":
                cats = (data.get("extra") or {}).get("categories") or {}
                for cat in list(cats.values())[:3]:
                    if isinstance(cat, str):
                        nid = add_node(f"category:{cat}", cat, "company")
                        edges.append({"source": root, "target": nid, "label": "categorized"})
            elif r.source == "username":
                for profile in (data.get("results") or []):
                    url = profile.get("profile_url")
                    if url:
                        nid = add_node(f"website:{url}", url, "website",
                                       data={"platform": profile.get("platform")})
                        edges.append({"source": root, "target": nid,
                                       "label": profile.get("platform", "")})
            elif r.source == "gravatar" and data.get("found"):
                accounts = data.get("accounts") or []
                for a in accounts[:5]:
                    if a.get("url"):
                        nid = add_node(f"website:{a['url']}", a["url"], "website",
                                       data={"platform": a.get("platform")})
                        edges.append({"source": root, "target": nid,
                                       "label": a.get("platform", "")})

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    def _build_summary(
        self,
        results: list[ProviderResult],
        confidence: float,
        ok_count: int,
        fail_count: int,
    ) -> dict[str, Any]:
        """Build a summary dict — backward compatible with the orchestrator's
        existing summary, plus a `confidence` field."""
        max_score = 0
        malicious = 0
        suspicious = 0
        for r in results:
            d = r.to_dict()
            if not d.get("ok"):
                continue
            data = d.get("data") or {}
            if isinstance(data.get("score"), (int, float)):
                max_score = max(max_score, int(data["score"]))
            malicious += int(data.get("malicious", 0) or 0)
            suspicious += int(data.get("suspicious", 0) or 0)

        if max_score >= 75:
            risk = "critical"
        elif max_score >= 50:
            risk = "high"
        elif max_score >= 25:
            risk = "medium"
        else:
            risk = "low"

        return {
            "risk": risk,
            "score": max_score,
            "malicious": malicious,
            "suspicious": suspicious,
            "threat_level": risk,
            "confidence": confidence,
        }


# --------------------------------------------------------------------------- #
# Module-level singleton
# --------------------------------------------------------------------------- #
_pipeline: InvestigationPipeline | None = None


def get_pipeline() -> InvestigationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = InvestigationPipeline()
    return _pipeline
