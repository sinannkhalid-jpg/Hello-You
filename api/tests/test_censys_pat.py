"""
Tests for the Censys PAT (Personal Access Token) migration.

Verifies:
  1. CENSYS_PAT → new Platform API v3 (Authorization: Bearer ...)
  2. CENSYS_API_ID + CENSYS_API_SECRET → legacy v1 (Authorization: Basic ...)
  3. PAT takes precedence when both are set
  4. Provider is auto-disabled when no credentials are set
  5. Health endpoint reflects the resolved auth mode
  6. Legacy endpoints still work (backward compat)
"""
from __future__ import annotations

import os
import tempfile

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

import importlib  # noqa: E402

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


def _reload_providers():
    """Re-import provider modules so the env vars are picked up fresh."""
    import app.services.providers.censys as censys_mod
    import app.services.providers.registry as reg
    import app.services.orchestrator as orch

    importlib.reload(censys_mod)
    importlib.reload(reg)
    importlib.reload(orch)
    return orch


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _register(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "verysecret123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


# --------------------------------------------------------------------------- #
# 1. PAT resolution at the module level
# --------------------------------------------------------------------------- #
def test_pat_takes_precedence():
    """When both CENSYS_PAT and the legacy ID/Secret are set, the PAT is used."""
    os.environ["CENSYS_PAT"] = "test-pat-token"
    os.environ["CENSYS_API_ID"] = "test-id"
    os.environ["CENSYS_API_SECRET"] = "test-secret"
    from app.services.providers.censys import _resolve_auth
    auth = _resolve_auth()
    assert auth is not None
    assert auth.mode == "pat"
    assert auth.token == "test-pat-token"
    assert auth.base_url == "https://api.platform.censys.io/v3"
    assert auth.host_path == "/global/host/{ip}"
    assert auth.authorization == "Bearer test-pat-token"
    print("[1] PAT takes precedence over legacy ID/Secret")


def test_legacy_fallback_when_pat_missing():
    """When only CENSYS_API_ID + CENSYS_API_SECRET are set, legacy auth is used."""
    os.environ.pop("CENSYS_PAT", None)
    os.environ["CENSYS_API_ID"] = "test-id"
    os.environ["CENSYS_API_SECRET"] = "test-secret"
    from app.services.providers.censys import _resolve_auth
    import base64
    auth = _resolve_auth()
    assert auth is not None
    assert auth.mode == "legacy"
    expected_token = base64.b64encode(b"test-id:test-secret").decode()
    assert auth.token == expected_token
    assert auth.authorization == f"Basic {expected_token}"
    assert auth.base_url == "https://search.censys.io/api/v1"
    assert auth.host_path == "/view/ipv4/{ip}"
    print("[2] legacy auth used when CENSYS_PAT is missing")


def test_no_auth_returns_none():
    """When no credentials are set, _resolve_auth returns None."""
    os.environ.pop("CENSYS_PAT", None)
    os.environ.pop("CENSYS_API_ID", None)
    os.environ.pop("CENSYS_API_SECRET", None)
    from app.services.providers.censys import _resolve_auth
    assert _resolve_auth() is None
    print("[3] no credentials → _resolve_auth returns None")


# --------------------------------------------------------------------------- #
# 4. Provider auto-disable when no credentials
# --------------------------------------------------------------------------- #
def test_provider_disabled_without_keys():
    os.environ.pop("CENSYS_PAT", None)
    os.environ.pop("CENSYS_API_ID", None)
    os.environ.pop("CENSYS_API_SECRET", None)
    orch_mod = _reload_providers()
    orch = orch_mod.get_orchestrator()
    censys = orch.providers.get("censys")
    assert censys is not None
    assert censys.enabled is False
    assert censys.api_key is None
    print("[4] provider disabled when no credentials are set")


# --------------------------------------------------------------------------- #
# 5. Provider enabled with PAT, health endpoint reflects auth mode
# --------------------------------------------------------------------------- #
def test_provider_enabled_with_pat():
    os.environ["CENSYS_PAT"] = "real-pat-here"
    os.environ.pop("CENSYS_API_ID", None)
    os.environ.pop("CENSYS_API_SECRET", None)
    orch_mod = _reload_providers()
    orch = orch_mod.get_orchestrator()
    censys = orch.providers.get("censys")
    assert censys is not None
    assert censys.enabled is True
    assert censys.api_key == "real-pat-here"
    assert censys._auth is not None
    assert censys._auth.mode == "pat"
    print("[5] provider enabled with PAT, _auth.mode == 'pat'")


def test_provider_enabled_with_legacy():
    os.environ.pop("CENSYS_PAT", None)
    os.environ["CENSYS_API_ID"] = "real-id"
    os.environ["CENSYS_API_SECRET"] = "real-secret"
    orch_mod = _reload_providers()
    orch = orch_mod.get_orchestrator()
    censys = orch.providers.get("censys")
    assert censys is not None
    assert censys.enabled is True
    assert censys._auth is not None
    assert censys._auth.mode == "legacy"
    assert censys.api_key == "real-id:real-secret"
    print("[6] provider enabled with legacy, _auth.mode == 'legacy'")


# --------------------------------------------------------------------------- #
# 7. URL building — pat vs legacy must hit the right endpoint
# --------------------------------------------------------------------------- #
def test_url_building_pat():
    os.environ["CENSYS_PAT"] = "abc"
    os.environ.pop("CENSYS_API_ID", None)
    os.environ.pop("CENSYS_API_SECRET", None)
    orch_mod = _reload_providers()
    orch = orch_mod.get_orchestrator()
    censys = orch.providers.get("censys")
    # Build what the URL *would* be (we don't actually call out)
    expected = "https://api.platform.censys.io/v3/global/host/8.8.8.8"
    actual = f"{censys._auth.base_url}{censys._auth.host_path.format(ip='8.8.8.8')}"
    assert actual == expected, f"PAT URL mismatch: {actual} != {expected}"
    assert censys._auth.authorization == "Bearer abc"
    print(f"[7] PAT URL: {actual}")


def test_url_building_legacy():
    os.environ.pop("CENSYS_PAT", None)
    os.environ["CENSYS_API_ID"] = "id"
    os.environ["CENSYS_API_SECRET"] = "sec"
    orch_mod = _reload_providers()
    orch = orch_mod.get_orchestrator()
    censys = orch.providers.get("censys")
    expected = "https://search.censys.io/api/v1/view/ipv4/8.8.8.8"
    actual = f"{censys._auth.base_url}{censys._auth.host_path.format(ip='8.8.8.8')}"
    assert actual == expected, f"legacy URL mismatch: {actual} != {expected}"
    assert censys._auth.authorization.startswith("Basic ")
    print(f"[8] legacy URL: {actual}")


# --------------------------------------------------------------------------- #
# 9. Health endpoint surfaces auth_mode
# --------------------------------------------------------------------------- #
async def test_health_includes_auth_mode():
    os.environ["CENSYS_PAT"] = "health-test-pat"
    os.environ.pop("CENSYS_API_ID", None)
    os.environ.pop("CENSYS_API_SECRET", None)
    _reload_providers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=15) as c:
        token = await _register(c, "censys-health@example.com")
        r = await c.get("/api/v1/intel/health?force=true", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        censys_health = next(
            (p for p in r.json().get("providers", []) if p["name"] == "censys"),
            None,
        )
        assert censys_health is not None
        assert censys_health.get("auth_mode") == "pat", f"expected auth_mode=pat, got {censys_health.get('auth_mode')}"
        print("[9] /intel/health surfaces auth_mode=pat for Censys")


# --------------------------------------------------------------------------- #
# 10. Backward compat — legacy endpoints untouched
# --------------------------------------------------------------------------- #
async def test_legacy_endpoints_intact():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=15) as c:
        # /health
        r = await c.get("/health")
        assert r.status_code == 200
        # /auth/register + /auth/me
        r = await c.post(
            "/api/v1/auth/register",
            json={"email": "compat2@example.com", "password": "verysecret123"},
        )
        assert r.status_code == 201
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        # /intel/providers
        r = await c.get("/api/v1/intel/providers", headers=h)
        assert r.status_code == 200
        # /intel/investigate still works
        r = await c.post(
            "/api/v1/intel/investigate",
            headers=h,
            json={"kind": "domain", "target": "example.com"},
        )
        assert r.status_code == 200
    print("[10] all legacy endpoints still work (health, auth, /intel/*)")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _run_sync():
    import asyncio
    asyncio.run(init_db())
    test_pat_takes_precedence()
    test_legacy_fallback_when_pat_missing()
    test_no_auth_returns_none()
    test_provider_disabled_without_keys()
    test_provider_enabled_with_pat()
    test_provider_enabled_with_legacy()
    test_url_building_pat()
    test_url_building_legacy()
    asyncio.run(test_health_includes_auth_mode())
    asyncio.run(test_legacy_endpoints_intact())


if __name__ == "__main__":
    _run_sync()
    print("=" * 60)
    print("ALL CENSYS PAT MIGRATION TESTS PASSED")
    print("=" * 60)
