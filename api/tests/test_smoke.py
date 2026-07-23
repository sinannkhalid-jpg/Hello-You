"""Smoke tests for the FastAPI app — exercise core endpoints without external APIs."""
from __future__ import annotations

import logging
import os
import tempfile

# Force SQLite before importing app modules.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "x" * 64

# silence SQLAlchemy DEBUG noise
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)

import asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402


async def _register_and_login(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "verysecret123", "full_name": "Tester"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


async def main() -> None:
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # health
        r = await c.get("/health")
        assert r.status_code == 200
        print("health ok")

        token = await _register_and_login(c)
        h = {"Authorization": f"Bearer {token}"}
        print("token len:", len(token))

        # me
        r = await c.get("/api/v1/auth/me", headers=h)
        print("me ->", r.status_code, r.text[:400])
        assert r.status_code == 200
        print("me ok ->", r.json()["email"])

        # dashboard
        r = await c.get("/api/v1/dashboard", headers=h)
        assert r.status_code == 200
        print("dashboard ok")

        # phone (no network)
        r = await c.get("/api/v1/phone/%2B14155552671", headers=h)
        print("phone ->", r.status_code, r.text[:300])
        assert r.status_code == 200
        print("phone ok ->", r.json()["country"])

        # investigations list (empty)
        r = await c.get("/api/v1/investigations", headers=h)
        assert r.status_code == 200
        print("investigations list ok ->", r.json())


if __name__ == "__main__":
    asyncio.run(main())
    os.unlink(_tmp.name)
    print("ALL OK")
