"""
Intel router — aggregate investigation endpoints.

New in this version:
  • POST /api/v1/intel/investigate      — full investigation (unchanged URL, richer response)
  • GET  /api/v1/intel/investigate/stream  — Server-Sent Events for live progress
  • GET  /api/v1/intel/investigate/export — PDF / JSON / CSV export
  • GET  /api/v1/intel/providers         — list providers (unchanged)
  • GET  /api/v1/intel/stats             — cache + rate-limit snapshot (unchanged)
  • GET  /api/v1/intel/health           — per-provider online/offline (unchanged)

The full investigation response is backward compatible with the previous
version: `target`, `kind`, `providers`, `summary`, `meta` keys are all
preserved. New keys (`confidence`, `evidence`, `graph`, `timeline`,
`progress`) are added so the frontend can render them.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field

from app.core.deps import CurrentUser
from app.services.exporter import to_csv, to_json, to_pdf
from app.services.orchestrator import get_orchestrator
from app.services.pipeline import get_pipeline

router = APIRouter(prefix="/intel", tags=["intel"])


# Health cache TTL — health checks ping real endpoints, so don't hammer them
_HEALTH_CACHE: dict[str, tuple[float, dict]] = {}
_HEALTH_TTL = 30.0  # seconds


class InvestigateRequest(BaseModel):
    kind: Literal["domain", "ip", "email", "username", "url"]
    target: str = Field(min_length=1, max_length=512)
    providers: list[str] | None = None


@router.post("/investigate")
async def investigate(
    body: InvestigateRequest,
    user: CurrentUser,
):
    pipeline = get_pipeline()
    return await pipeline.run(body.kind, body.target, providers=body.providers)


@router.get("/investigate/stream")
async def investigate_stream(
    user: CurrentUser,
    kind: Literal["domain", "ip", "email", "username", "url"],
    target: str = Query(min_length=1, max_length=512),
    providers: str | None = Query(None, description="Comma-separated provider filter"),
):
    """Server-Sent Events stream of the investigation.

    The client opens this URL with EventSource and receives one event per
    progress stage. The final event has `stage: "result"` and contains
    the complete investigation response.
    """
    provider_list = (
        [p.strip() for p in providers.split(",") if p.strip()]
        if providers
        else None
    )
    pipeline = get_pipeline()

    async def event_gen():
        try:
            async for event in pipeline.stream(
                kind, target, providers=provider_list
            ):
                yield f"event: {event.get('stage', 'message')}\ndata: {json.dumps(event, default=str)}\n\n"
        except Exception as e:  # noqa: BLE001
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/investigate/export")
async def investigate_export(
    user: CurrentUser,
    kind: Literal["domain", "ip", "email", "username", "url"],
    target: str = Query(min_length=1, max_length=512),
    fmt: Literal["pdf", "csv", "json"] = "pdf",
):
    """Run an investigation and export the report as PDF/JSON/CSV."""
    pipeline = get_pipeline()
    result = await pipeline.run(kind, target)

    if fmt == "pdf":
        data = to_pdf(result)
        media = "application/pdf"
        ext = "pdf"
    elif fmt == "csv":
        data = to_csv(result)
        media = "text/csv"
        ext = "csv"
    else:
        data = to_json(result)
        media = "application/json"
        ext = "json"

    fname = f"investigation-{kind}-{target}.{ext}"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.get("/providers")
async def list_providers(user: CurrentUser):
    """List all registered providers and their config (key presence redacted)."""
    return get_orchestrator().list_providers()


@router.get("/stats")
async def stats(user: CurrentUser):
    """Inspect cache + rate limiter state. Useful for ops."""
    return get_orchestrator().stats()


@router.get("/health")
async def health(user: CurrentUser, force: bool = False):
    """Probe each enabled provider.

    For each provider we issue a lightweight GET against its `health_url`
    (or fall back to the default). Results are cached for 30s to avoid
    hammering upstream services. Pass `?force=true` to bypass the cache.
    """
    orch = get_orchestrator()
    now = time.time()
    if not force:
        cached = _HEALTH_CACHE.get("all")
        if cached and (now - cached[0]) < _HEALTH_TTL:
            return cached[1]

    async def _probe(name: str, prov) -> dict:
        if not force:
            cp = _HEALTH_CACHE.get(name)
            if cp and (now - cp[0]) < _HEALTH_TTL:
                return cp[1]
        info = {
            "name": prov.name,
            "kind": prov.kind,
            "enabled": prov.enabled,
            "requires_key": prov.requires_key,
            "has_key": bool(prov.api_key),
        }
        # Surface which auth mode the provider is using (helps verify
        # that PAT vs legacy is wired correctly after a key change).
        auth_mode = getattr(prov, "_auth", None)
        if auth_mode is not None and hasattr(auth_mode, "mode"):
            info["auth_mode"] = auth_mode.mode
        if not prov.enabled:
            info.update({"status": "disabled", "ok": False})
            _HEALTH_CACHE[name] = (now, info)
            return info
        if prov.requires_key and not prov.api_key:
            info.update({"status": "no_api_key", "ok": False})
            _HEALTH_CACHE[name] = (now, info)
            return info
        try:
            res = await prov.healthcheck()
            info.update({
                "status": "online" if res.get("ok") else "offline",
                "ok": bool(res.get("ok")),
                "duration_ms": res.get("duration_ms", 0),
                "detail": res.get("detail"),
            })
        except Exception as e:  # noqa: BLE001
            info.update({"status": "offline", "ok": False, "error": str(e)[:160]})
        _HEALTH_CACHE[name] = (now, info)
        return info

    probes = [_probe(p.name, p) for p in orch.providers.values()]
    results = await asyncio.gather(*probes, return_exceptions=True)
    final: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            final.append({"name": "?", "status": "offline", "ok": False, "error": str(r)[:160]})
        else:
            final.append(r)

    online = sum(1 for r in final if r.get("status") == "online")
    offline = sum(1 for r in final if r.get("status") == "offline")
    other = len(final) - online - offline
    summary = {
        "total": len(final),
        "online": online,
        "offline": offline,
        "disabled_or_unconfigured": other,
    }
    response = {
        "checked_at": now,
        "ttl_seconds": _HEALTH_TTL,
        "summary": summary,
        "providers": final,
    }
    _HEALTH_CACHE["all"] = (now, response)
    return response
