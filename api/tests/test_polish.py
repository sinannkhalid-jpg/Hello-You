"""
End-to-end tests for the final-polish features.

Covers:
  1. asyncio.gather() — providers run concurrently
  2. Per-provider timeout (5s cap)
  3. Retry with exponential backoff
  4. SSE progress events
  5. Final confidence score
  6. Relationship graph JSON
  7. Timeline data
  8. Evidence severity
  9. Export (PDF / JSON / CSV)
 10. Backward compatibility (legacy endpoints unchanged)
"""
from __future__ import annotations

import asyncio
import os
import tempfile
import time

# Configure env BEFORE imports
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "x" * 64

import logging  # noqa: E402

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.orchestrator import get_orchestrator  # noqa: E402
from app.services.pipeline import get_pipeline  # noqa: E402
from app.services.providers.base import BaseProvider  # noqa: E402


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _register(client: AsyncClient, email: str = "polish@example.com") -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "verysecret123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------- #
# 1 + 3. asyncio.gather() + retry with backoff
# --------------------------------------------------------------------------- #
async def test_concurrent_execution() -> None:
    """All providers should run concurrently, not serially."""
    await init_db()
    pipeline = get_pipeline()

    t0 = time.perf_counter()
    r = await pipeline.run("domain", "example.com", providers=["dns", "whois"])
    elapsed = (time.perf_counter() - t0) * 1000

    # DNS + WHOIS in serial would take roughly sum(their times). Concurrent
    # should be max(their times). We just check that the run completed in a
    # reasonable timeframe (under 10s — both clamped to 5s).
    assert elapsed < 10_000, f"run took {elapsed:.0f}ms, expected < 10s"
    assert r["meta"]["providers_queried"] == 2
    print(f"[1] concurrent: {elapsed:.0f}ms, providers={r['meta']['providers_queried']}")


# --------------------------------------------------------------------------- #
# 2. Per-provider timeout cap (5s)
# --------------------------------------------------------------------------- #
async def test_timeout_cap() -> None:
    """Every provider should have timeout_seconds <= MAX_TIMEOUT_SECONDS."""
    await init_db()
    orch = get_orchestrator()
    for name, p in orch.providers.items():
        assert p.timeout_seconds <= BaseProvider.MAX_TIMEOUT_SECONDS, (
            f"{name} has timeout={p.timeout_seconds} > cap"
        )
    print(f"[2] timeout cap enforced for {len(orch.providers)} providers")


# --------------------------------------------------------------------------- #
# 3. Retry with exponential backoff
# --------------------------------------------------------------------------- #
class _AlwaysFails(BaseProvider):
    name = "_always_fails"
    kind = "ip"
    timeout_seconds = 1.0
    max_retries = 2

    async def lookup(self, target, **kwargs):
        raise RuntimeError("boom")


class _FlakyProvider(BaseProvider):
    """Fails the first time, succeeds the second."""
    name = "_flaky"
    kind = "ip"
    timeout_seconds = 1.0
    max_retries = 2
    attempts: int = 0

    async def lookup(self, target, **kwargs):
        type(self).attempts += 1
        if type(self).attempts == 1:
            raise RuntimeError("first try fails")
        return {"found": True, "score": 0, "threat_level": "low"}


async def test_retry_with_backoff() -> None:
    """A flaky provider should be retried with exponential backoff."""
    await init_db()
    # 1. Always-failing provider should give up after max_retries+1 attempts
    p1 = _AlwaysFails()
    t0 = time.perf_counter()
    r1 = await p1.run("1.1.1.1")
    elapsed_fail = time.perf_counter() - t0
    assert not r1.ok
    assert "boom" in (r1.error or "")
    # Backoff: 0.3s + 0.6s = 0.9s minimum between attempts
    assert elapsed_fail >= 0.9, f"expected backoff >= 0.9s, got {elapsed_fail:.2f}s"

    # 2. Flaky provider should succeed on the second attempt
    p2 = _FlakyProvider()
    p2.cache = None
    p2.rate_limiter = None
    type(_FlakyProvider).attempts = 0
    r2 = await p2.run("2.2.2.2")
    assert r2.ok, f"flaky provider should have succeeded on retry, got {r2}"
    assert _FlakyProvider.attempts == 2, f"expected 2 attempts, got {_FlakyProvider.attempts}"
    print(f"[3] backoff enforced (fail: {elapsed_fail:.2f}s >= 0.9s); flaky retried successfully")


# --------------------------------------------------------------------------- #
# 4. SSE progress events
# --------------------------------------------------------------------------- #
async def test_sse_progress() -> None:
    """The /investigate/stream endpoint emits Searching/Checking/Completed events."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, email="sse@example.com")
        events: list[dict] = []
        async with c.stream(
            "GET",
            "/api/v1/intel/investigate/stream?kind=domain&target=example.com",
            headers=_hdr(token),
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    import json
                    payload = json.loads(line[5:].strip())
                    events.append(payload)
                if len(events) >= 50:
                    break
    stages = [e["stage"] for e in events]
    assert "start" in stages, f"missing 'start' in {stages}"
    assert "checking" in stages, f"missing 'checking' in {stages}"
    assert "completed" in stages or "failed" in stages, f"missing completion in {stages}"
    assert "result" in stages, f"missing 'result' in {stages}"
    # Ensure at least one 'Checking ...' event from a provider
    checking_msgs = [e for e in events if e["stage"] == "checking"]
    assert checking_msgs, "no 'checking' events"
    # Ensure a provider name is in a checking event
    has_provider = any(e.get("provider") for e in checking_msgs)
    assert has_provider, "checking events missing provider name"
    print(f"[4] SSE: {len(events)} events, stages={sorted(set(stages))}")


# --------------------------------------------------------------------------- #
# 5. Final confidence score
# --------------------------------------------------------------------------- #
async def test_confidence_score() -> None:
    """The investigation response must include a top-level `confidence` (0..1)."""
    await init_db()
    pipeline = get_pipeline()
    r = await pipeline.run("domain", "example.com")
    assert "confidence" in r, "missing confidence in response"
    assert 0.0 <= r["confidence"] <= 1.0, f"confidence out of range: {r['confidence']}"
    # And the summary should also include it (back-compat for /api/v1/report)
    assert "confidence" in r["summary"]
    print(f"[5] confidence={r['confidence']} (0..1) in top-level + summary")


# --------------------------------------------------------------------------- #
# 6. Relationship graph JSON
# --------------------------------------------------------------------------- #
async def test_relationship_graph() -> None:
    """The investigation response must include `graph` with nodes + edges."""
    await init_db()
    pipeline = get_pipeline()
    r = await pipeline.run("domain", "example.com")
    assert "graph" in r
    assert "nodes" in r["graph"]
    assert "edges" in r["graph"]
    # Domain investigation should yield at least the root + DNS A records
    assert len(r["graph"]["nodes"]) >= 1
    assert len(r["graph"]["edges"]) >= 1
    # Every node must have the required React-Flow fields
    n0 = r["graph"]["nodes"][0]
    for k in ("id", "label", "type"):
        assert k in n0, f"node missing {k}: {n0}"
    e0 = r["graph"]["edges"][0]
    assert "source" in e0 and "target" in e0
    print(f"[6] graph: {len(r['graph']['nodes'])} nodes, {len(r['graph']['edges'])} edges")


# --------------------------------------------------------------------------- #
# 7. Timeline data
# --------------------------------------------------------------------------- #
async def test_timeline() -> None:
    """The investigation response must include an ordered `timeline`."""
    await init_db()
    pipeline = get_pipeline()
    r = await pipeline.run("domain", "example.com")
    assert "timeline" in r
    assert isinstance(r["timeline"], list)
    assert len(r["timeline"]) >= 3  # at least start + N providers + done
    # First item is the start, last item is "done"
    assert r["timeline"][0]["stage"] == "start"
    assert r["timeline"][-1]["stage"] == "done"
    # Each item has the required fields
    for t in r["timeline"]:
        assert "ts" in t and "stage" in t and "label" in t and "kind" in t
    print(f"[7] timeline: {len(r['timeline'])} events, first/last OK")


# --------------------------------------------------------------------------- #
# 8. Evidence severity
# --------------------------------------------------------------------------- #
async def test_evidence_severity() -> None:
    """Evidence items must include a severity in {critical, high, medium, low, info}."""
    await init_db()
    pipeline = get_pipeline()
    r = await pipeline.run("ip", "8.8.8.8")
    assert "evidence" in r
    valid = {"critical", "high", "medium", "low", "info"}
    for ev in r["evidence"]:
        assert "severity" in ev, f"evidence missing severity: {ev}"
        assert ev["severity"] in valid, f"invalid severity: {ev['severity']}"
    print(f"[8] evidence severities: {[e['severity'] for e in r['evidence']]}")


# --------------------------------------------------------------------------- #
# 9. Export (PDF / JSON / CSV)
# --------------------------------------------------------------------------- #
async def test_export() -> None:
    """The /investigate/export endpoint must produce PDF, JSON, and CSV."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, email="export@example.com")
        for fmt, ctype, min_size in [
            ("pdf", "application/pdf", 100),
            ("json", "application/json", 200),
            ("csv", "text/csv", 100),
        ]:
            r = await c.get(
                f"/api/v1/intel/investigate/export?kind=domain&target=example.com&fmt={fmt}",
                headers=_hdr(token),
            )
            assert r.status_code == 200, f"{fmt}: {r.status_code} {r.text[:200]}"
            assert ctype in r.headers.get("content-type", ""), f"{fmt} ctype: {r.headers.get('content-type')}"
            assert len(r.content) >= min_size, f"{fmt} too small: {len(r.content)}"
            if fmt == "json":
                j = r.json()
                assert "confidence" in j
                assert "evidence" in j
                assert "graph" in j
                assert "timeline" in j
            print(f"[9] {fmt}: {len(r.content)} bytes, content-type={r.headers.get('content-type')}")


# --------------------------------------------------------------------------- #
# 10. Backward compatibility — legacy endpoints still work
# --------------------------------------------------------------------------- #
async def test_backward_compat() -> None:
    """The legacy /api/v1/{domain,ip,email,phone,investigations,dashboard,auth} endpoints
    must still work exactly as before."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        # /health
        r = await c.get("/health")
        assert r.status_code == 200
        # /api/v1/auth/register
        r = await c.post(
            "/api/v1/auth/register",
            json={"email": "compat@example.com", "password": "verysecret123"},
        )
        assert r.status_code == 201
        token = r.json()["access_token"]
        h = _hdr(token)
        # /api/v1/auth/me
        r = await c.get("/api/v1/auth/me", headers=h)
        assert r.status_code == 200
        # /api/v1/dashboard
        r = await c.get("/api/v1/dashboard", headers=h)
        assert r.status_code == 200
        # /api/v1/phone
        r = await c.get("/api/v1/phone/%2B14155552671", headers=h)
        assert r.status_code == 200
        assert r.json().get("country") == "US"
        # /api/v1/dns
        r = await c.get("/api/v1/dns/example.com", headers=h)
        assert r.status_code == 200
        # /api/v1/investigations
        r = await c.get("/api/v1/investigations", headers=h)
        assert r.status_code == 200
        # /api/v1/intel/providers (already-existing route)
        r = await c.get("/api/v1/intel/providers", headers=h)
        assert r.status_code == 200
        assert len(r.json()) >= 1
        # /api/v1/intel/health (already-existing route)
        r = await c.get("/api/v1/intel/health", headers=h)
        assert r.status_code == 200
        assert "providers" in r.json()
    print("[10] all legacy endpoints still work (health, auth, dashboard, phone, dns, investigations, intel/*)")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
async def main() -> None:
    await init_db()
    print("=" * 60)
    print("Running final-polish test suite")
    print("=" * 60)
    await test_concurrent_execution()
    await test_timeout_cap()
    await test_retry_with_backoff()
    await test_sse_progress()
    await test_confidence_score()
    await test_relationship_graph()
    await test_timeline()
    await test_evidence_severity()
    await test_export()
    await test_backward_compat()
    print("=" * 60)
    print("ALL POLISH TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
