"""
Tests for the comprehensive audit work in this turn.

Verifies:
  1. Username provider now has 36 platforms, blocks and not-founds
     are reported separately.
  2. Email provider returns DKIM/MTA-STS/TLS/BIMI/DNSSEC/RDAP/git-leaks
     and provider diagnostics.
  3. Phone provider returns full OSINT with messaging, portability,
     reputation (each with explicit "unavailable - <reason>" text).
  4. /api/v1/config/audit endpoint lists every API with required
     env vars.
  5. The new structured "reason" fields are present on every
     provider-conditional field.
"""
from __future__ import annotations

import os
import tempfile

# Configure env BEFORE imports
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
from app.services.orchestrator import get_orchestrator  # noqa: E402


# --------------------------------------------------------------------------- #
# Username provider
# --------------------------------------------------------------------------- #
async def test_username_36_platforms() -> None:
    """The provider must support 36 platforms (up from 29)."""
    from app.services.providers.username import PLATFORMS
    names = {p.name for p in PLATFORMS}
    assert len(PLATFORMS) == 36, f"Expected 36 platforms, got {len(PLATFORMS)}"
    # New platforms from this turn
    for required in ("LeetCode", "Codeforces", "npm", "DockerHub",
                     "PyPI", "Kaggle", "Discord"):
        assert required in names, f"Missing required platform: {required}"
    print(f"[1] 36 platforms: {sorted(names)[:8]}... ({len(names)} total)")


async def test_username_blocked_and_not_found() -> None:
    """When a platform is blocked, it must be reported separately from
    'not found'."""
    orch = get_orchestrator()
    # Use a user we know is on at least one platform AND triggers
    # some blocked platforms (Instagram, Threads are rate-limited;
    # Discord has no public API).
    r = await orch.investigate("username", "sindresorhus", providers=["username"])
    d = r["providers"]["username"]["data"]
    assert "blocked" in d, f"Missing 'blocked' field: {list(d)}"
    assert "not_found" in d, f"Missing 'not_found' field: {list(d)}"
    print(f"[2] sindresorhus: {d['count']} found, "
          f"{len(d['blocked'])} blocked, {len(d['not_found'])} not_found")


# --------------------------------------------------------------------------- #
# Email provider
# --------------------------------------------------------------------------- #
async def test_email_gmail_dkim_found() -> None:
    """Gmail must now show DKIM as found (previously reported as missing)."""
    from app.osint.email_provider import dkim_record
    result = dkim_record("gmail.com")
    assert result["found"] is True, f"Gmail DKIM not found: {result}"
    assert result["selector"] in ("20161025", "20210112", "20230712")
    print(f"[3] Gmail DKIM: selector={result['selector']}")


async def test_email_outlook_dkim_found() -> None:
    from app.osint.email_provider import dkim_record
    result = dkim_record("outlook.com")
    assert result["found"] is True, f"Outlook DKIM not found: {result}"
    print(f"[4] Outlook DKIM: selector={result['selector']}")


async def test_email_yahoo_dkim_found() -> None:
    from app.osint.email_provider import dkim_record
    result = dkim_record("yahoo.com")
    assert result["found"] is True, f"Yahoo DKIM not found: {result}"
    print(f"[5] Yahoo DKIM: selector={result['selector']}")


async def test_email_classify_provider() -> None:
    from app.osint.email_provider import classify_provider
    gmail = classify_provider("gmail.com")
    assert gmail["is_free_mail"] is True
    assert gmail["provider"] == "Gmail"
    mailinator = classify_provider("mailinator.com")
    assert mailinator["is_disposable"] is True
    assert mailinator["provider"] == "Disposable"
    custom = classify_provider("example.com")
    assert custom["provider"] == "Custom"
    assert custom["is_free_mail"] is False
    print("[6] classify_provider: Gmail / Outlook / Disposable / Custom all work")


async def test_email_full_intel_fields() -> None:
    """The full email response must include all the new fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        # Register a user
        await ac.post("/api/v1/auth/register", json={
            "email": "audit-test@example.com",
            "password": "AuditTest123!",
            "full_name": "Audit Test",
        })
        # Login
        r = await ac.post("/api/v1/auth/login", json={
            "email": "audit-test@example.com",
            "password": "AuditTest123!",
        })
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Now hit the email endpoint
        r = await ac.get("/api/v1/email/sinankhalid88@gmail.com", headers=h)
        assert r.status_code == 200, f"email endpoint returned {r.status_code}: {r.text}"
        d = r.json()
        # Required new fields
        for f in ("provider", "is_free_mail", "is_disposable",
                  "dkim", "mta_sts", "tls", "dnssec", "nameservers",
                  "breach_exposure", "git_leaks", "leakcheck",
                  "reputation", "providers", "duration_ms"):
            assert f in d, f"Missing field {f} in email response: {list(d)}"
        # DKIM must be found
        assert d["dkim"]["found"] is True, f"Gmail DKIM should be found: {d['dkim']}"
        # provider must be Gmail
        assert d["provider"] == "Gmail"
        # diagnostics must include HIBP, Gravatar, etc.
        assert "hibp" in d["providers"]
        assert "gravatar" in d["providers"]
        assert d["providers"]["hibp"]["configured"] is False
        assert d["providers"]["hibp"]["reason"] == "no_api_key"
        print(f"[7] email response: provider={d['provider']}, "
              f"DKIM={d['dkim']['selector']}, "
              f"MTA-STS={d['mta_sts']['enabled']}, "
              f"reputation.score={d['reputation']['score']}")


# --------------------------------------------------------------------------- #
# Phone provider
# --------------------------------------------------------------------------- #
async def test_phone_indian_mobile() -> None:
    """Test an Indian mobile number with full OSINT fields."""
    from app.osint.phone_provider import async_enrichment, lookup
    d = lookup("+919747173130")
    d = await async_enrichment(d)
    assert d["valid"] is True
    assert d["country"] == "IN"
    assert d["country_name"] == "India"
    assert d["is_mobile"] is True
    assert d["number_type_name"] == "MOBILE"
    assert d["timezone"] == "Asia/Calcutta"
    # Messaging must have all three platforms
    for plat in ("whatsapp", "telegram", "signal"):
        assert plat in d["messaging"], f"missing {plat}"
        assert "reason" in d["messaging"][plat]
    # Portability must have reason
    assert "reason" in d["portability"]
    print(f"[8] Indian mobile: country={d['country_name']}, "
          f"carrier={d['carrier']}, type={d['number_type_name']}")


async def test_phone_invalid_returns_structured_error() -> None:
    """An invalid phone number must return a structured error, not crash."""
    from app.osint.phone_provider import lookup
    d = lookup("not-a-phone")
    assert d["valid"] is False
    assert d["e164"] == ""
    # Must have a reason
    assert d.get("reason") == "parse_failed"
    # All messaging fields must have reasons
    assert d["messaging"]["whatsapp"]["reason"] == "no_public_api"
    print("[9] Invalid phone: structured error returned, no crash")


# --------------------------------------------------------------------------- #
# Config audit endpoint
# --------------------------------------------------------------------------- #
async def test_config_audit_lists_every_api() -> None:
    """The /api/v1/config/audit endpoint must list every external API."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        await ac.post("/api/v1/auth/register", json={
            "email": "audit-test2@example.com",
            "password": "AuditTest123!",
            "full_name": "Audit Test 2",
        })
        r = await ac.post("/api/v1/auth/login", json={
            "email": "audit-test2@example.com",
            "password": "AuditTest123!",
        })
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        r = await ac.get("/api/v1/config/audit", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["summary"]["total"] >= 10
        names = {a["name"] for a in d["apis"]}
        for api in ("Censys", "VirusTotal", "AbuseIPDB", "Shodan",
                    "Have I Been Pwned", "Gravatar", "LeakCheck",
                    "SecurityTrails"):
            assert api in names, f"audit missing API: {api}"
        # Each entry must have the required fields
        for entry in d["apis"]:
            for f in ("name", "configured", "reason", "required_variables",
                      "missing_variables", "provider_status"):
                assert f in entry, f"missing {f} in {entry.get('name')}"
            # If missing, must have a reason
            if not entry["configured"]:
                assert "Missing" in entry["reason"] or "key" in entry["reason"].lower(), \
                    f"missing reason: {entry}"
        print(f"[10] config audit: {d['summary']['total']} APIs, "
              f"{d['summary']['missing_key']} missing keys")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
async def main() -> None:
    await init_db()
    print("=" * 60)
    print("Comprehensive audit tests")
    print("=" * 60)
    await test_username_36_platforms()
    await test_username_blocked_and_not_found()
    await test_email_gmail_dkim_found()
    await test_email_outlook_dkim_found()
    await test_email_yahoo_dkim_found()
    await test_email_classify_provider()
    await test_email_full_intel_fields()
    await test_phone_indian_mobile()
    await test_phone_invalid_returns_structured_error()
    await test_config_audit_lists_every_api()
    print("=" * 60)
    print("ALL COMPREHENSIVE AUDIT TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
