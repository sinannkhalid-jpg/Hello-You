"""
End-to-end audit of every public endpoint.

Each endpoint is called with a known-good input and the result is
classified as OK / SLOW / FAIL. The test is non-fatal: it prints a
report and exits 0 even if some endpoints fail (the goal is
visibility, not blocking CI).
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


ENDPOINTS = [
    ("GET",  "/health",                         None,                       None),
    ("GET",  "/api/v1/dashboard",               None,                       None),
    ("GET",  "/api/v1/phone/%2B14155552671",     None,                       None),
    ("GET",  "/api/v1/email/ada@example.com",    None,                       None),
    ("GET",  "/api/v1/email/sindresorhus@gmail.com", None,                  None),
    ("GET",  "/api/v1/email/this_xyz_12345_abc_does_not_exist@example.com", None, None),
    ("GET",  "/api/v1/username/octocat",        None,                       None),
    ("GET",  "/api/v1/username/sindresorhus",    None,                       None),
    ("GET",  "/api/v1/domain/example.com",       None,                       None),
    ("GET",  "/api/v1/ip/8.8.8.8",              None,                       None),
    ("GET",  "/api/v1/dns/example.com",          None,                       None),
    ("GET",  "/api/v1/whois/google.com",         None,                       None),
    ("GET",  "/api/v1/ssl/example.com",          None,                       None),
    ("GET",  "/api/v1/ct/example.com?limit=5",   None,                       None),
    ("GET",  "/api/v1/subdomains/example.com",   None,                       None),
    ("GET",  "/api/v1/tech/example.com",         None,                       None),
    ("GET",  "/api/v1/intel/providers",          None,                       None),
    ("GET",  "/api/v1/intel/health",             None,                       None),
    ("GET",  "/api/v1/intel/stats",              None,                       None),
    ("POST", "/api/v1/intel/investigate",
        {"kind": "domain", "target": "example.com"}, None),
    ("POST", "/api/v1/intel/investigate",
        {"kind": "ip", "target": "8.8.8.8"},     None),
    ("POST", "/api/v1/intel/investigate",
        {"kind": "email", "target": "test@gmail.com"}, None),
    ("POST", "/api/v1/intel/investigate",
        {"kind": "username", "target": "octocat"}, None),
    # Edge cases / error inputs — these SHOULD NOT 5xx
    ("GET",  "/api/v1/email/not-an-email",       None,                       None),
    ("GET",  "/api/v1/domain/..bad..",           None,                       None),
    ("GET",  "/api/v1/ip/999.999.999.999",       None,                       None),
    ("GET",  "/api/v1/username/!!",              None,                       None),
    ("POST", "/api/v1/intel/investigate",        {"kind": "wat", "target": "x"}, None),

    # Unauthenticated requests — should 401, not 500
    ("GET",  "/api/v1/dashboard",               None,                       "NO_AUTH"),
    ("GET",  "/api/v1/email/ada@example.com",    None,                       "NO_AUTH"),
    ("GET",  "/api/v1/username/octocat",        None,                       "NO_AUTH"),
    ("POST", "/api/v1/intel/investigate",        {"kind": "domain", "target": "example.com"}, "NO_AUTH"),
]


async def main() -> None:
    await init_db()
    print("=" * 80)
    print("ENDPOINT AUDIT — Hello You backend")
    print("=" * 80)
    fails: list[tuple[str, str, int, str]] = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t", timeout=60) as c:
        r = await c.post("/api/v1/auth/register",
                         json={"email": "audit@example.com", "password": "verysecret123"})
        if r.status_code != 201:
            print(f"register failed: {r.status_code} {r.text[:200]}")
            return
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        for method, path, body, flag in ENDPOINTS:
            # Use a fresh client per request so an unhandled exception
            # in one endpoint doesn't kill the audit loop.
            try:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://t", timeout=30
                ) as c2:
                    headers = {} if flag == "NO_AUTH" else h
                    if method == "GET":
                        r = await c2.get(path, headers=headers, timeout=30.0)
                    else:
                        r = await c2.post(path, headers=headers, json=body, timeout=30.0)
                    tag = "OK " if r.status_code == 200 else f"FAIL {r.status_code}"
                    print(f"  {method:4s} {path:62s} {tag:10s} {r.text[:60]!r}")
                    # 401 is acceptable for NO_AUTH tests
                    if r.status_code != 200 and not (flag == "NO_AUTH" and r.status_code == 401):
                        fails.append((method, path, r.status_code, r.text[:200]))
            except Exception as e:
                print(f"  {method:4s} {path:62s} EXCEPTION {type(e).__name__}: {str(e)[:100]}")
                fails.append((method, path, -1, str(e)[:200]))

    print("=" * 80)
    if fails:
        print(f"{len(fails)} FAILURES:")
        for m, p, s, body in fails:
            print(f"  [{s}] {m} {p}")
            print(f"        {body}")
    else:
        print("ALL ENDPOINTS OK")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
