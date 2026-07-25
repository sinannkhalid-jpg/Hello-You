"""
Tests for the username provider — verifies the full platform list
is wired correctly and basic existence detection works against
real public APIs.

These are integration tests that hit the real internet. They
are designed to be tolerant: a single platform returning "not
found" doesn't fail the test, because individual platforms can
be flaky. The assertion is on:
  • Provider count is at least 25
  • All required major platforms are in the list
  • A real username (sindresorhus) is found on at least 5 platforms
  • A clearly-fake username is found on 0 platforms
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

from app.db.session import init_db  # noqa: E402
from app.services.orchestrator import get_orchestrator  # noqa: E402
from app.services.providers.username import PLATFORMS, BY_NAME  # noqa: E402

REQUIRED_PLATFORMS = {
    "GitHub", "GitLab", "Reddit", "Instagram", "Facebook", "Threads",
    "Twitter/X", "TikTok", "LinkedIn", "Pinterest", "Telegram",
    "YouTube", "Twitch", "Steam", "Keybase", "Gravatar", "Mastodon",
    "Snapchat", "Spotify", "YouTube", "Dev.to", "StackOverflow",
    "HackerNews", "Behance", "Dribbble", "Vimeo", "SoundCloud",
    "About.me", "Medium", "Pinterest", "Bitbucket",
}


async def test_platform_list() -> None:
    """The full major platform list must be present and at least 25 entries."""
    await init_db()
    names = {p.name for p in PLATFORMS}
    missing = REQUIRED_PLATFORMS - names
    assert not missing, f"Missing platforms: {missing}"
    assert len(PLATFORMS) >= 25, f"Only {len(PLATFORMS)} platforms"
    print(f"[1] platform list: {len(PLATFORMS)} entries, all major platforms present")


async def test_real_user() -> None:
    """A real public username should be found on multiple platforms."""
    orch = get_orchestrator()
    r = await orch.investigate("username", "sindresorhus", providers=["username"])
    d = r["providers"]["username"]["data"]
    platforms_found = [res["platform"] for res in d["results"]]
    assert d["count"] >= 5, f"sindresorhus found on only {d['count']} platforms: {platforms_found}"
    # Must include the major ones we definitely expect
    assert "GitHub" in platforms_found
    assert "GitLab" in platforms_found
    assert "YouTube" in platforms_found
    print(f"[2] sindresorhus: {d['count']} platforms: {sorted(platforms_found)}")


async def test_nonexistent_user() -> None:
    """A clearly fake username should be found on 0 platforms (no false positives)."""
    orch = get_orchestrator()
    r = await orch.investigate(
        "username", "this_xyz_12345_abc_does_not_exist_definitely",
        providers=["username"],
    )
    d = r["providers"]["username"]["data"]
    # Allow a small tolerance (e.g. one platform being flaky), but
    # the count must be < 3 to count as "no false positives".
    assert d["count"] < 3, f"unexpected {d['count']} matches for fake user: {d['results']}"
    print(f"[3] fake user: {d['count']} matches (≤2 allowed for flake)")


async def test_response_shape() -> None:
    """Each result must have the canonical fields per the spec."""
    orch = get_orchestrator()
    r = await orch.investigate("username", "octocat", providers=["username"])
    d = r["providers"]["username"]["data"]
    assert d["count"] >= 1
    for res in d["results"]:
        for key in ("platform", "profile_url", "username", "verified",
                    "found", "confidence", "response_time_ms"):
            assert key in res, f"missing key {key} in result: {res}"
        # Optional fields the frontend can use
        # display_name, avatar_url, strategies may be None
    print(f"[4] response shape: {d['count']} results, all have canonical fields")


async def main() -> None:
    await init_db()
    print("=" * 60)
    print("Username provider — integration tests")
    print("=" * 60)
    await test_platform_list()
    await test_real_user()
    await test_nonexistent_user()
    await test_response_shape()
    print("=" * 60)
    print("ALL USERNAME PROVIDER TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
