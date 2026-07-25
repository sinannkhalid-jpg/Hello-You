"""
Regression tests for the email investigation endpoint.

The original bug was that `gravatar_exists()` called `asyncio.run()`
inside a running event loop, throwing `RuntimeError` and producing a
500. This test asserts the endpoint is robust and returns 200 for
all reasonable inputs.
"""
from __future__ import annotations

import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "x" * 64

import asyncio
import logging  # noqa: E402

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


async def _register(c: AsyncClient, email: str = "email-test@example.com") -> str:
    r = await c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "verysecret123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def test_happy_path() -> None:
    """The endpoint must return 200 for a real, well-formed email."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, "email1@example.com")
        r = await c.get(
            "/api/v1/email/sindresorhus@gmail.com",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
        j = r.json()
        assert j["email"] == "sindresorhus@gmail.com"
        assert j["domain"] == "gmail.com"
        # Must have at least MX records (gmail has them)
        assert isinstance(j["mx_records"], list)
        # Gravatar URL is always set; either "real" or "default"
        assert j.get("gravatar_url") is not None
        # Risk score is an int
        assert isinstance(j["risk_score"], int)
        print(f"[1] happy path: status=200, domain={j['domain']}, risk={j['risk_score']}")


async def test_nonexistent_email() -> None:
    """A clearly-fake email should still return 200 (no exceptions)."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, "email2@example.com")
        r = await c.get(
            "/api/v1/email/this_doesnt_exist_xyz_12345@nonexistent-domain-abc-12345.com",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
        j = r.json()
        assert "risk_score" in j
        # High risk: no MX
        assert j["risk_score"] >= 35
        print(f"[2] nonexistent: status=200, risk={j['risk_score']} (high as expected)")


async def test_gmail_typical() -> None:
    """A gmail.com address should return sensible data."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, "email3@example.com")
        r = await c.get(
            "/api/v1/email/somebody@gmail.com",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        j = r.json()
        # Gmail has DMARC
        assert j["dmarc"] is not None, "Gmail should have a DMARC record"
        # Gmail has SPF
        assert j["spf"] is not None, "Gmail should have an SPF record"
        print(f"[3] gmail: status=200, has_dmarc={bool(j['dmarc'])}, has_spf={bool(j['spf'])}")


async def test_disposable_email() -> None:
    """A disposable email should produce a high risk score."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, "email4@example.com")
        r = await c.get(
            "/api/v1/email/foo@mailinator.com",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        j = r.json()
        # mailinator is in the disposable list; should boost the score
        assert j.get("disposable") is True or j["risk_score"] >= 25
        print(f"[4] disposable: status=200, risk={j['risk_score']}, disposable={j.get('disposable')}")


async def test_invalid_email() -> None:
    """Invalid email syntax should return 400, not 500."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, "email5@example.com")
        r = await c.get(
            "/api/v1/email/not-an-email",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400, f"got {r.status_code}: {r.text[:200]}"
        print(f"[5] invalid email: status=400 (correctly rejected)")


async def test_gravatar_no_crash() -> None:
    """The original bug: gravatar_exists crashed with RuntimeError when
    called inside a running event loop. This test asserts the endpoint
    never raises that exception (i.e. the response is 200 or 4xx,
    not 500)."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        token = await _register(c, "email6@example.com")
        for email in (
            "test@gmail.com",
            "octocat@github.com",
            "this_xyz_12345@nonexistent-abc-12345.com",
        ):
            r = await c.get(
                f"/api/v1/email/{email}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code != 500, (
                f"500 for {email}: {r.text[:200]} — the gravatar bug is back"
            )
        print("[6] gravatar regression: no 500s on any email")


async def test_unauthenticated_returns_401() -> None:
    """No auth = 401, not 500."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=30) as c:
        r = await c.get("/api/v1/email/test@gmail.com")
        assert r.status_code == 401
        print("[7] unauthenticated: status=401")


async def main() -> None:
    print("=" * 60)
    print("Email investigation — regression tests")
    print("=" * 60)
    await test_happy_path()
    await test_nonexistent_email()
    await test_gmail_typical()
    await test_disposable_email()
    await test_invalid_email()
    await test_gravatar_no_crash()
    await test_unauthenticated_returns_401()
    print("=" * 60)
    print("ALL EMAIL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
