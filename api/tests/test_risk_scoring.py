"""
Tests for the unified Risk Score system.

Risk Score = 0-100, higher = more risky.
Bands:
  0-20   Low Risk   (green  #22c55e)
  21-40  Guarded    (lime   #84cc16)
  41-60  Moderate   (amber  #f59e0b)
  61-80  High Risk  (orange #f97316)
  81-100 Critical   (red    #ef4444)

This test file verifies:
  1. The canonical risk classification returns the right band.
  2. The `risk_score_for_email` function produces sensible numbers
     and respects both positive (negative mail config) and negative
     (properly configured mail) signals.
  3. The HTTP API exposes `risk_score` (int) and `risk_level`
     (canonical name) consistently.
  4. The legacy `threat_level` / `reputation` fields are still
     present for back-compat.
  5. There is NO instance where a high reputation score
     produces a "critical" classification.
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

from app.core.risk import (  # noqa: E402
    RISK_BANDS, classify, classes_for, color_for, from_legacy_threat_level,
    normalize_level,
)
from app.db.session import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.osint.email_provider import risk_score_for_email  # noqa: E402


# --------------------------------------------------------------------------- #
# Pure unit tests on the classifier
# --------------------------------------------------------------------------- #
def test_classify_low_risk() -> None:
    """0-20 must be Low Risk (green)."""
    for s in (0, 1, 10, 20):
        c = classify(s)
        assert c["risk_score"] == s
        assert c["risk_level"] == "Low Risk", f"score={s} → {c['risk_level']}"
        assert c["color"] == "#22c55e"


def test_classify_guarded() -> None:
    """21-40 must be Guarded (lime)."""
    for s in (21, 30, 40):
        c = classify(s)
        assert c["risk_level"] == "Guarded", f"score={s} → {c['risk_level']}"
        assert c["color"] == "#84cc16"


def test_classify_moderate() -> None:
    """41-60 must be Moderate (amber)."""
    for s in (41, 50, 60):
        c = classify(s)
        assert c["risk_level"] == "Moderate", f"score={s} → {c['risk_level']}"
        assert c["color"] == "#f59e0b"


def test_classify_high_risk() -> None:
    """61-80 must be High Risk (orange)."""
    for s in (61, 70, 80):
        c = classify(s)
        assert c["risk_level"] == "High Risk", f"score={s} → {c['risk_level']}"
        assert c["color"] == "#f97316"


def test_classify_critical() -> None:
    """81-100 must be Critical (red)."""
    for s in (81, 89, 90, 100):
        c = classify(s)
        assert c["risk_level"] == "Critical", f"score={s} → {c['risk_level']}"
        assert c["color"] == "#ef4444"


def test_classify_clamps() -> None:
    """Out-of-range values are clamped to 0 or 100."""
    assert classify(-50)["risk_score"] == 0
    assert classify(-50)["risk_level"] == "Low Risk"
    assert classify(250)["risk_score"] == 100
    assert classify(250)["risk_level"] == "Critical"
    assert classify(None)["risk_score"] == 0


def test_normalize_level_accepts_legacy() -> None:
    """The legacy short tokens must be normalized to canonical names."""
    assert normalize_level("low") == "Low Risk"
    assert normalize_level("guarded") == "Guarded"
    assert normalize_level("medium") == "Moderate"
    assert normalize_level("high") == "High Risk"
    assert normalize_level("critical") == "Critical"


def test_normalize_level_passes_through_canonical() -> None:
    """Canonical names pass through unchanged."""
    for n in ("Low Risk", "Guarded", "Moderate", "High Risk", "Critical"):
        assert normalize_level(n) == n


def test_color_for_uses_canonical_name() -> None:
    """`color_for` returns the right hex for any token or name."""
    assert color_for("low") == "#22c55e"
    assert color_for("Low Risk") == "#22c55e"
    assert color_for("critical") == "#ef4444"
    assert color_for("Critical") == "#ef4444"


def test_classes_for_returns_useful_classes() -> None:
    assert "border" in classes_for("Critical")
    assert "text" in classes_for("Critical")
    assert classes_for("high") == classes_for("High Risk")


# --------------------------------------------------------------------------- #
# Test the email risk computation
# --------------------------------------------------------------------------- #
def test_email_risk_well_configured_is_low() -> None:
    """A well-configured corporate email should have low risk."""
    risk = risk_score_for_email(
        mx=[{"priority": 10, "host": "mail.example.com"}],
        spf="v=spf1 -all",
        dkim={"found": True, "selector": "default", "value": "..."},
        dmarc="v=DMARC1; p=reject;",
        mta_sts={"enabled": True, "mode": "enforce"},
        tls={"checked": 3, "supports_tls": 3, "details": []},
        dnssec={"enabled": True, "reason": None},
        gravatar={"exists": True, "url": "..."},
        breach={"found": False, "count": 0, "breaches": []},
        git_leaks={"found": False, "count": 0, "commits": []},
        classification={"is_free_mail": False, "is_disposable": False, "provider": "Custom"},
        domain_age={"age_days": 3650, "registrar": "GoDaddy"},
    )
    assert risk["risk_score"] <= 20, f"Well-configured: {risk}"
    assert risk["risk_level"] == "Low Risk"


def test_email_risk_disposable_is_critical() -> None:
    """A disposable email with no SPF/DKIM/DMARC must be Critical or High."""
    risk = risk_score_for_email(
        mx=[{"priority": 10, "host": "mail.example.com"}],
        spf=None,
        dkim={"found": False, "selector": None, "value": None},
        dmarc=None,
        mta_sts={"enabled": False, "mode": None},
        tls={"checked": 1, "supports_tls": 0, "details": []},
        dnssec={"enabled": False, "reason": "not_validated"},
        gravatar={"exists": False, "url": None},
        breach={"found": True, "count": 3, "breaches": []},
        git_leaks={"found": True, "count": 1, "commits": []},
        classification={"is_free_mail": False, "is_disposable": True, "provider": "Disposable"},
        domain_age={"age_days": 5, "registrar": "GoDaddy"},
    )
    assert risk["risk_score"] >= 81, f"Disposable + breaches should be critical: {risk}"
    assert risk["risk_level"] == "Critical"
    # Findings should explain the score
    assert any("Disposable" in f for f in risk["findings"])
    assert any("breach" in f for f in risk["findings"])


def test_email_risk_breach_increases_score() -> None:
    """A breach with proper mail config should still raise the score."""
    base_args = dict(
        mx=[{"priority": 10, "host": "mail.example.com"}],
        spf="v=spf1 -all",
        dkim={"found": True, "selector": "default", "value": "..."},
        dmarc="v=DMARC1; p=reject;",
        mta_sts={"enabled": True, "mode": "enforce"},
        tls={"checked": 3, "supports_tls": 3, "details": []},
        dnssec={"enabled": True, "reason": None},
        gravatar={"exists": True, "url": "..."},
        classification={"is_free_mail": False, "is_disposable": False, "provider": "Custom"},
        domain_age={"age_days": 3650, "registrar": "GoDaddy"},
    )
    no_breach = risk_score_for_email(
        **base_args,
        breach={"found": False, "count": 0, "breaches": []},
        git_leaks={"found": False, "count": 0, "commits": []},
    )
    with_breach = risk_score_for_email(
        **base_args,
        breach={"found": True, "count": 5, "breaches": []},
        git_leaks={"found": False, "count": 0, "commits": []},
    )
    assert with_breach["risk_score"] > no_breach["risk_score"], (
        f"Breach should increase risk: {no_breach} -> {with_breach}"
    )


def test_email_risk_dkim_missing_increases_score() -> None:
    """Missing DKIM should increase the score."""
    base_args = dict(
        mx=[{"priority": 10, "host": "mail.example.com"}],
        spf="v=spf1 -all",
        dmarc="v=DMARC1; p=reject;",
        mta_sts={"enabled": True, "mode": "enforce"},
        tls={"checked": 3, "supports_tls": 3, "details": []},
        dnssec={"enabled": True, "reason": None},
        gravatar={"exists": True, "url": "..."},
        breach={"found": False, "count": 0, "breaches": []},
        git_leaks={"found": False, "count": 0, "commits": []},
        classification={"is_free_mail": False, "is_disposable": False, "provider": "Custom"},
        domain_age={"age_days": 3650, "registrar": "GoDaddy"},
    )
    with_dkim = risk_score_for_email(
        **base_args,
        dkim={"found": True, "selector": "default", "value": "..."},
    )
    without_dkim = risk_score_for_email(
        **base_args,
        dkim={"found": False, "selector": None, "value": None},
    )
    assert without_dkim["risk_score"] > with_dkim["risk_score"]


def test_email_risk_dnssec_missing_increases_score() -> None:
    """Missing DNSSEC should increase the score."""
    base_args = dict(
        mx=[{"priority": 10, "host": "mail.example.com"}],
        spf="v=spf1 -all",
        dkim={"found": True, "selector": "default", "value": "..."},
        dmarc="v=DMARC1; p=reject;",
        mta_sts={"enabled": True, "mode": "enforce"},
        tls={"checked": 3, "supports_tls": 3, "details": []},
        gravatar={"exists": True, "url": "..."},
        breach={"found": False, "count": 0, "breaches": []},
        git_leaks={"found": False, "count": 0, "commits": []},
        classification={"is_free_mail": False, "is_disposable": False, "provider": "Custom"},
        domain_age={"age_days": 3650, "registrar": "GoDaddy"},
    )
    with_dnssec = risk_score_for_email(
        **base_args,
        dnssec={"enabled": True, "reason": None},
    )
    without_dnssec = risk_score_for_email(
        **base_args,
        dnssec={"enabled": False, "reason": "not_validated"},
    )
    assert without_dnssec["risk_score"] > with_dnssec["risk_score"]


def test_email_risk_score_is_clamped_to_100() -> None:
    """A worst-case scenario must clamp to 100, not exceed it."""
    risk = risk_score_for_email(
        mx=[],
        spf=None,
        dkim={"found": False, "selector": None, "value": None},
        dmarc=None,
        mta_sts={"enabled": False, "mode": None},
        tls={"checked": 0, "supports_tls": 0, "details": []},
        dnssec={"enabled": False, "reason": "not_validated"},
        gravatar={"exists": False, "url": None},
        breach={"found": True, "count": 50, "breaches": []},
        git_leaks={"found": True, "count": 100, "commits": []},
        classification={"is_free_mail": False, "is_disposable": True, "provider": "Disposable"},
        domain_age={"age_days": 1, "registrar": "GoDaddy"},
    )
    assert risk["risk_score"] == 100
    assert risk["risk_level"] == "Critical"


# --------------------------------------------------------------------------- #
# HTTP API tests — verify the response shape
# --------------------------------------------------------------------------- #
async def test_email_response_uses_risk_level_canonical() -> None:
    """The API response must use the canonical risk_level name (not
    'threat_level' or a short token like 'critical')."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        await ac.post("/api/v1/auth/register", json={
            "email": "risk-test@example.com",
            "password": "RiskTest123!",
            "full_name": "Risk Test",
        })
        r = await ac.post("/api/v1/auth/login", json={
            "email": "risk-test@example.com",
            "password": "RiskTest123!",
        })
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # Test 1: A clearly problematic (disposable + no mail config) email
        r = await ac.get("/api/v1/email/foo@mailinator.com", headers=h)
        assert r.status_code == 200
        d = r.json()
        # risk_score is a number 0-100
        assert isinstance(d["risk_score"], int)
        assert 0 <= d["risk_score"] <= 100
        # risk_level is the canonical name
        assert d["risk_level"] in ("Low Risk", "Guarded", "Moderate", "High Risk", "Critical")
        # risk dict has score/level/color/findings
        assert d["risk"]["level"] == d["risk_level"]
        assert d["risk"]["score"] == d["risk_score"]
        # risk.color is hex
        assert d["risk"]["color"].startswith("#")
        # The reputation (legacy) field is still there, but it must be
        # CONSISTENT with risk: same score, same band name.
        assert d["reputation"]["score"] == d["risk_score"]
        # threat_level (legacy token) is also there for back-compat
        assert d["threat_level"] in ("low", "guarded", "medium", "high", "critical")
        print(f"[1] mailinator: risk_score={d['risk_score']} risk_level={d['risk_level']}")


async def test_email_response_score_matches_level() -> None:
    """No 'higher = safer' mismatch: a low risk_score must never be
    classified as Critical, and a high risk_score must never be Low."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        await ac.post("/api/v1/auth/register", json={
            "email": "score-test@example.com",
            "password": "ScoreTest123!",
            "full_name": "Score Test",
        })
        r = await ac.post("/api/v1/auth/login", json={
            "email": "score-test@example.com",
            "password": "ScoreTest123!",
        })
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        # mailinator: should be at least Moderate (it has real DNS so it
        # won't be Critical, but the disposable flag must push it up)
        r = await ac.get("/api/v1/email/foo@mailinator.com", headers=h)
        d = r.json()
        # Score is moderate or higher
        assert d["risk_score"] >= 40, f"Disposable should be ≥ Moderate: {d['risk_score']}"
        # The label is at least Moderate
        assert d["risk_level"] in ("Moderate", "High Risk", "Critical"), (
            f"Score {d['risk_score']} should be Moderate+, got {d['risk_level']}"
        )
        # Gmail: low risk
        r = await ac.get("/api/v1/email/sinankhalid88@gmail.com", headers=h)
        d = r.json()
        # Gmail is well-configured
        assert d["risk_score"] <= 50, f"Gmail should not be high risk: {d['risk_score']}"
        # The label must not be Critical for a low score
        assert d["risk_level"] != "Critical", (
            f"Low score must not be Critical, got {d['risk_level']}"
        )
        print(f"[2] gmail: risk_score={d['risk_score']} risk_level={d['risk_level']}")


async def main() -> None:
    print("=" * 60)
    print("Risk Score system — tests")
    print("=" * 60)
    test_classify_low_risk()
    print("[1] 0-20 → Low Risk (green)")
    test_classify_guarded()
    print("[2] 21-40 → Guarded (lime)")
    test_classify_moderate()
    print("[3] 41-60 → Moderate (amber)")
    test_classify_high_risk()
    print("[4] 61-80 → High Risk (orange)")
    test_classify_critical()
    print("[5] 81-100 → Critical (red)")
    test_classify_clamps()
    print("[6] classify clamps out-of-range scores")
    test_normalize_level_accepts_legacy()
    print("[7] normalize_level accepts legacy short tokens")
    test_normalize_level_passes_through_canonical()
    print("[8] normalize_level passes canonical names through")
    test_color_for_uses_canonical_name()
    print("[9] color_for returns the right hex")
    test_classes_for_returns_useful_classes()
    print("[10] classes_for returns usable Tailwind classes")
    test_email_risk_well_configured_is_low()
    print("[11] well-configured email → Low Risk")
    test_email_risk_disposable_is_critical()
    print("[12] disposable + breaches → Critical")
    test_email_risk_breach_increases_score()
    print("[13] breach increases risk score")
    test_email_risk_dkim_missing_increases_score()
    print("[14] missing DKIM increases risk score")
    test_email_risk_dnssec_missing_increases_score()
    print("[15] missing DNSSEC increases risk score")
    test_email_risk_score_is_clamped_to_100()
    print("[16] risk score clamped to 100")
    await init_db()
    await test_email_response_uses_risk_level_canonical()
    print("[17] email API uses canonical risk_level name")
    await test_email_response_score_matches_level()
    print("[18] no 'higher = safer' mismatch in API response")
    print("=" * 60)
    print("ALL RISK SCORE TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
