"""Relationship graph router.

Builds an entity graph for a given investigation: the target entity is
linked to other entities discovered during the investigation (MX hosts,
NS hosts, IPs from A records, emails of admins found in WHOIS, etc.).
The graph is rendered on the frontend with React Flow.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db
from app.models.investigation import Investigation
from app.schemas.osint import GraphEdge, GraphNode, GraphResult

router = APIRouter(prefix="/graph", tags=["graph"])


def _add_node(nodes: dict[str, GraphNode], ntype: str, label: str, data: dict | None = None) -> str:
    nid = f"{ntype}:{label}".lower()
    if nid not in nodes:
        nodes[nid] = GraphNode(id=nid, label=label, type=ntype, data=data or {})
    return nid


@router.get("/investigation/{inv_id}", response_model=GraphResult)
async def from_investigation(
    inv_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    inv = (await db.execute(
        select(Investigation).where(Investigation.id == inv_id, Investigation.user_id == user.id)
    )).scalar_one_or_none()
    if not inv:
        raise HTTPException(404, "Investigation not found")

    return GraphResult(**_build(inv.kind, inv.target, inv.result or {}))


@router.post("/from-data", response_model=GraphResult)
async def from_data(
    payload: dict,
    user: CurrentUser,
):
    kind = payload.get("kind") or "domain"
    target = payload.get("target") or ""
    data = payload.get("data") or {}
    return GraphResult(**_build(kind, target, data))


def _build(kind: str, target: str, data: dict) -> dict:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    root = _add_node(nodes, kind, target, {"root": True})

    if kind == "domain":
        for ip in (data.get("dns", {}) or {}).get("a", []):
            nid = _add_node(nodes, "ip", ip)
            edges.append(GraphEdge(source=root, target=nid, label="A"))
        for ip in (data.get("dns", {}) or {}).get("aaaa", []):
            nid = _add_node(nodes, "ip", ip)
            edges.append(GraphEdge(source=root, target=nid, label="AAAA"))
        for mx in (data.get("dns", {}) or {}).get("mx", []):
            host = mx.get("host") if isinstance(mx, dict) else None
            if host:
                nid = _add_node(nodes, "domain", host)
                edges.append(GraphEdge(source=root, target=nid, label=f"MX {mx.get('priority')}"))
        for ns in (data.get("dns", {}) or {}).get("ns", []):
            nid = _add_node(nodes, "domain", ns)
            edges.append(GraphEdge(source=root, target=nid, label="NS"))
        cdn = data.get("cdn")
        if cdn:
            nid = _add_node(nodes, "company", cdn)
            edges.append(GraphEdge(source=root, target=nid, label="CDN"))
        hosting = data.get("hosting")
        if hosting:
            nid = _add_node(nodes, "company", hosting)
            edges.append(GraphEdge(source=root, target=nid, label="hosting"))
    elif kind == "ip":
        rdns = data.get("reverse_dns")
        if rdns:
            nid = _add_node(nodes, "domain", rdns)
            edges.append(GraphEdge(source=root, target=nid, label="PTR"))
        isp = data.get("isp")
        if isp:
            nid = _add_node(nodes, "company", isp)
            edges.append(GraphEdge(source=root, target=nid, label="ISP"))
        for p in data.get("open_ports", []):
            nid = _add_node(nodes, "ip", f"{target}:{p}")
            edges.append(GraphEdge(source=root, target=nid, label=f"port {p}"))
    elif kind == "email":
        domain = data.get("domain")
        if domain:
            nid = _add_node(nodes, "domain", domain)
            edges.append(GraphEdge(source=root, target=nid, label="@"))
        for mx in data.get("mx_records", []):
            host = mx.get("host") if isinstance(mx, dict) else None
            if host:
                nid = _add_node(nodes, "domain", host)
                edges.append(GraphEdge(source=nid, target=root, label="MX"))
    elif kind == "username":
        for p in data.get("profiles", []):
            url = p.get("url") if isinstance(p, dict) else None
            if url:
                nid = _add_node(nodes, "website", url, {"platform": p.get("platform")})
                edges.append(GraphEdge(source=root, target=nid, label=p.get("platform", "")))

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }
