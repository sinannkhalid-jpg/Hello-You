"""
Username provider — multi-strategy existence detection across 30+ public
platforms.

Each `Platform` is a thin declarative object that points to one or more
`checker` async callables. A checker is responsible for sending the
HTTP request(s) it needs and returning a `dict` with at minimum
`ok` and `found` keys, plus optional `display_name`, `bio`,
`avatar_url`, and `extra`.

We never bypass authentication, never run JavaScript, and never
scrape private endpoints. The checkers are designed to be tolerant of
layout changes: ambiguous responses are treated as "not found" rather
than "found", to keep false positives low.

A platform is reported as `found=True` only if at least one
*strong* checker returns a positive result. Confidence is the
agreement ratio of all checkers × a per-platform base reliability.

The response per profile contains:

    platform         : str
    profile_url      : str
    username         : str
    display_name     : str | None
    bio              : str | None
    avatar_url       : str | None
    verified         : bool
    found            : bool
    confidence       : float  # 0..1
    response_time_ms : int
    strategies       : list[dict]  # per-checker results
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx

from app.core.logging import get_logger
from app.services.providers.base import BaseProvider
from app.services.providers.username_helpers import (
    DEFAULT_UA, _client_headers, parse_meta, pick_avatar,
    pick_display_name, safe_get, title_of,
    check_aboutme, check_behance, check_bitbucket, check_codeforces,
    check_devto, check_discord, check_dockerhub, check_dribbble,
    check_facebook, check_github, check_gitlab, check_gravatar,
    check_hackernews, check_instagram, check_kaggle, check_keybase,
    check_leetcode, check_linkedin, check_mastodon, check_medium,
    check_npm, check_pinterest, check_pypi, check_reddit, check_snapchat,
    check_soundcloud, check_spotify, check_stackoverflow, check_steam,
    check_telegram, check_threads, check_tiktok, check_twitch,
    check_twitter_x, check_vimeo, check_youtube,
)

log = get_logger("username")


# --------------------------------------------------------------------------- #
# Platform definition
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Platform:
    name: str
    primary_url: str                        # profile URL template
    reliable: bool = True                   # downgrades ambiguous results
    checkers: tuple = ()                    # async (client, username) -> dict
    notes: str = ""

    def build(self, username: str) -> str:
        return self.primary_url.format(u=username)


# --------------------------------------------------------------------------- #
# Platform registry
#
# Each entry has a primary URL, an ordered list of `checker` callables,
# and a `reliable` flag. The list is ordered roughly from most-authoritative
# signal (official JSON API, oEmbed) to weakest (HTML heuristics).
# --------------------------------------------------------------------------- #
PLATFORMS: list[Platform] = [
    # ---- Code & Tech ----
    Platform("GitHub",       "https://github.com/{u}",           reliable=True,
             checkers=(check_github,)),
    Platform("GitLab",       "https://gitlab.com/{u}",           reliable=True,
             checkers=(check_gitlab,)),
    Platform("Bitbucket",    "https://bitbucket.org/{u}/",       reliable=True,
             checkers=(check_bitbucket,)),
    Platform("StackOverflow","https://stackoverflow.com/users/{u}", reliable=True,
             checkers=(check_stackoverflow,)),
    Platform("Dev.to",       "https://dev.to/{u}",               reliable=True,
             checkers=(check_devto,)),
    Platform("HackerNews",   "https://news.ycombinator.com/user?id={u}", reliable=True,
             checkers=(check_hackernews,)),
    Platform("Keybase",      "https://keybase.io/{u}",           reliable=True,
             checkers=(check_keybase,)),

    # ---- Social (reliable APIs or oEmbed) ----
    Platform("Reddit",       "https://www.reddit.com/user/{u}",  reliable=True,
             checkers=(check_reddit,)),
    Platform("YouTube",      "https://www.youtube.com/@{u}",     reliable=True,
             checkers=(check_youtube,)),
    Platform("TikTok",       "https://www.tiktok.com/@{u}",     reliable=True,
             checkers=(check_tiktok,)),
    Platform("Mastodon",     "https://mastodon.social/@{u}",    reliable=True,
             checkers=(check_mastodon,)),
    Platform("Twitch",       "https://www.twitch.tv/{u}",       reliable=True,
             checkers=(check_twitch,)),
    Platform("Steam",        "https://steamcommunity.com/id/{u}", reliable=True,
             checkers=(check_steam,)),
    Platform("Spotify",      "https://open.spotify.com/user/{u}", reliable=True,
             checkers=(check_spotify,)),

    # ---- Social (HTML heuristics — reliable=False) ----
    Platform("Twitter/X",    "https://x.com/{u}",               reliable=False,
             checkers=(check_twitter_x,),
             notes="Size signature; JS-rendered so display_name is unavailable."),
    Platform("Instagram",    "https://www.instagram.com/{u}/",   reliable=False,
             checkers=(check_instagram,),
             notes="Checks og:image meta tag."),
    Platform("Facebook",     "https://www.facebook.com/{u}",     reliable=False,
             checkers=(check_facebook,),
             notes="Distinguishes by page size and login interstitial."),
    Platform("Threads",      "https://www.threads.net/@{u}",    reliable=False,
             checkers=(check_threads,),
             notes="Same meta pattern as Instagram."),
    Platform("LinkedIn",     "https://www.linkedin.com/in/{u}", reliable=False,
             checkers=(check_linkedin,),
             notes="Returns 999 for missing users."),
    Platform("Pinterest",    "https://www.pinterest.com/{u}/",  reliable=True,
             checkers=(check_pinterest,)),
    Platform("Snapchat",     "https://www.snapchat.com/add/{u}", reliable=True,
             checkers=(check_snapchat,),
             notes="Real profiles are ~100KB; missing pages are ~7KB."),
    Platform("Telegram",     "https://t.me/{u}",                reliable=True,
             checkers=(check_telegram,)),

    # ---- Design / Creative ----
    Platform("Behance",      "https://www.behance.net/{u}",     reliable=True,
             checkers=(check_behance,)),
    Platform("Dribbble",     "https://dribbble.com/{u}",        reliable=True,
             checkers=(check_dribbble,)),
    Platform("Vimeo",        "https://vimeo.com/{u}",           reliable=True,
             checkers=(check_vimeo,)),
    Platform("SoundCloud",   "https://soundcloud.com/{u}",      reliable=True,
             checkers=(check_soundcloud,)),

    # ---- Identity / Misc ----
    Platform("Gravatar",     "https://www.gravatar.com/{u}",    reliable=True,
             checkers=(check_gravatar,)),
    Platform("Medium",       "https://medium.com/@{u}",         reliable=False,
             checkers=(check_medium,),
             notes="Often Cloudflare-challenged; some users can be confirmed."),
    Platform("About.me",     "https://about.me/{u}",            reliable=True,
             checkers=(check_aboutme,)),

    # ---- Code, packages, communities ----
    Platform("LeetCode",     "https://leetcode.com/{u}",        reliable=True,
             checkers=(check_leetcode,)),
    Platform("Codeforces",   "https://codeforces.com/profile/{u}", reliable=True,
             checkers=(check_codeforces,)),
    Platform("npm",          "https://www.npmjs.com/~{u}",      reliable=True,
             checkers=(check_npm,),
             notes="Profile page is Cloudflare-protected; checked via registry author search."),
    Platform("DockerHub",    "https://hub.docker.com/u/{u}",    reliable=True,
             checkers=(check_dockerhub,)),
    Platform("PyPI",         "https://pypi.org/user/{u}/",      reliable=False,
             checkers=(check_pypi,),
             notes="Profile page is Cloudflare-protected; checked via search results."),
    Platform("Kaggle",       "https://www.kaggle.com/{u}",      reliable=False,
             checkers=(check_kaggle,),
             notes="Profile page is reCAPTCHA-protected; reports blocked."),
    Platform("Discord",      "https://discord.com/users/{u}",   reliable=False,
             checkers=(check_discord,),
             notes="No public username lookup API. Reported as blocked."),
]


BY_NAME: dict[str, Platform] = {p.name: p for p in PLATFORMS}


# --------------------------------------------------------------------------- #
# Provider
# --------------------------------------------------------------------------- #
class UsernameProvider(BaseProvider):
    name = "username"
    kind = "username"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 60
    cache_ttl = 60 * 30
    # The username lookup fans out to 30+ platforms in parallel, so a
    # single 5s outer cap is too tight. The orchestrator raises the cap
    # to 30s for providers that set `allow_long_timeout = True`.
    timeout_seconds = 30.0
    allow_long_timeout = True
    health_url = "https://github.com/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        username = target.strip().lstrip("@")
        if not username or len(username) > 64 or not re.match(r"^[A-Za-z0-9._-]+$", username):
            return {
                "username": username,
                "count": 0,
                "results": [],
                "confidence": 0.0,
                "total_checked": 0,
                "duration_ms": 0,
            }

        wanted = None
        if kwargs.get("platforms"):
            wanted = {p.strip().lower() for p in kwargs["platforms"].split(",") if p.strip()}
        platforms = [p for p in PLATFORMS if not wanted or p.name.lower() in wanted]

        # Concurrency control: 6 platforms in flight at a time
        outer = asyncio.Semaphore(6)
        async with httpx.AsyncClient(
            headers={"User-Agent": DEFAULT_UA},
            follow_redirects=True,
            http2=False,
            timeout=8.0,
        ) as client:
            tasks = [self._check_platform(client, outer, p, username) for p in platforms]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        final: list[dict[str, Any]] = []
        blocked_list: list[dict[str, Any]] = []
        not_found_list: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            if not r:
                continue
            if r.get("blocked"):
                blocked_list.append(r)
            elif r.get("found"):
                final.append(r)
            else:
                not_found_list.append(r)

        final.sort(key=lambda x: (x["confidence"], -x["response_time_ms"]), reverse=True)
        blocked_list.sort(key=lambda x: x["platform"])
        not_found_list.sort(key=lambda x: x["platform"])
        avg_conf = round(
            sum(f["confidence"] for f in final) / len(final), 2
        ) if final else 0.0
        return {
            "username": username,
            "count": len(final),
            "results": final,
            "blocked": blocked_list,
            "not_found": not_found_list,
            "confidence": avg_conf,
            "total_checked": len(platforms),
        }

    async def _check_platform(
        self,
        client: httpx.AsyncClient,
        sem: asyncio.Semaphore,
        platform: Platform,
        username: str,
    ) -> dict[str, Any] | None:
        if not platform.checkers:
            return None

        t0 = time.perf_counter()
        async with sem:
            runs = await asyncio.gather(
                *(checker(client, username) for checker in platform.checkers),
                return_exceptions=False,
            )

        # Combine checker results
        yes: list[dict] = []
        no: list[dict] = []
        blocked: list[dict] = []
        fields: dict[str, Any] = {}
        strategy_log: list[dict[str, Any]] = []
        for r in runs:
            strategy_log.append({
                "ok": r.get("ok", False),
                "found": r.get("found", False),
                "status": r.get("status"),
                "size": r.get("size"),
                "error": r.get("error"),
                "extra_reason": (r.get("extra") or {}).get("reason"),
            })
            if r.get("found") and r.get("ok"):
                yes.append(r)
                for k in ("display_name", "bio", "avatar_url"):
                    if not fields.get(k) and r.get(k):
                        fields[k] = r[k]
            elif r.get("ok") and r.get("found") is False:
                no.append(r)
            elif r.get("ok") and r.get("found") is None:
                # Blocked: rate-limited, Cloudflare, reCAPTCHA, no API, etc.
                blocked.append(r)

        yes_weight = len(yes)
        no_weight = len(no)
        blocked_weight = len(blocked)
        total = yes_weight + no_weight
        response_time_ms = int((time.perf_counter() - t0) * 1000)

        if total == 0 and blocked_weight == 0:
            return None

        # Blocked-only: no signal either way. Surface the platform as
        # "unavailable" so the caller can show "Instagram: rate-limited"
        # instead of pretending the user is or isn't there.
        if total == 0 and blocked_weight > 0:
            extra = blocked[0].get("extra") or {}
            return {
                "platform": platform.name,
                "profile_url": platform.build(username),
                "username": username,
                "display_name": None,
                "bio": None,
                "avatar_url": None,
                "verified": False,
                "found": None,
                "blocked": True,
                "block_reason": extra.get("reason", "unknown"),
                "block_detail": extra.get("detail"),
                "confidence": 0.0,
                "response_time_ms": response_time_ms,
                "reliable": platform.reliable,
                "strategies": strategy_log,
            }

        # Confidence: ratio of yes votes × reliability base
        agreement = yes_weight / total
        base = 0.9 if platform.reliable else 0.55
        # Bonus for having display_name + avatar (strong corroboration)
        bonus = 0.1 if (fields.get("display_name") and fields.get("avatar_url")) else 0
        confidence = round(min(0.99, base * agreement + bonus), 2)

        # If the platform is unreliable, require a yes vote to count as found
        found = yes_weight > 0
        if not platform.reliable and not found:
            found = False
            confidence = min(confidence, 0.4)

        return {
            "platform": platform.name,
            "profile_url": platform.build(username),
            "username": username,
            "display_name": fields.get("display_name"),
            "bio": fields.get("bio"),
            "avatar_url": fields.get("avatar_url"),
            "verified": found,
            "found": found,
            "blocked": False,
            "confidence": confidence,
            "response_time_ms": response_time_ms,
            "reliable": platform.reliable,
            "strategies": strategy_log,
        }
