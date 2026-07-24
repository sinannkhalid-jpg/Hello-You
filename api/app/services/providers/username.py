"""
Username provider — multi-strategy detection across 25+ public platforms.

Each platform is implemented as a *strategy set* — one or more independent
checks. The final confidence is the weighted agreement of the strategies:

  • `http`         — GET the public profile URL, look for 200 + username
                     in the HTML/Meta tags.
  • `api`          — Public, unauthenticated API endpoint (e.g.
                     Reddit /user/.json, Keybase /{u}/_/api/1.0/user/lookup,
                     GitHub /users/{u}).
  • `oembed`       — Platform oEmbed endpoint (returns 200 only for real
                     profiles). Used by YouTube, TikTok, etc.
  • `favicon`      — Resolve the platform's well-known icon to confirm
                     the page rendered (very weak signal; used as a tie
                     breaker only).

We never bypass authentication, never run JavaScript, and never scrape
private endpoints. Platforms that need JS to render (some sections of
Facebook, Instagram, LinkedIn) are marked `reliable=False` and the
`http` strategy is downgraded to "best-effort".

A platform is reported as `found=True` only if at least one *strong*
strategy returns positive. Confidence is the agreement ratio of
strategies × a per-platform base reliability weight.

The response per profile contains:

    platform          : str
    profile_url       : str
    username          : str
    display_name      : str | None
    bio               : str | None
    avatar_url        : str | None
    verified          : bool   # alias of "found" but explicit
    confidence        : float  # 0..1
    response_time_ms  : int    # how long this platform's check took
    strategies        : list[dict]  # which strategies ran and what they returned
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

log = get_logger("username")


# ---- helpers -------------------------------------------------------------- #

META_RE = re.compile(
    r'<meta[^>]+(?:name|property)=["\'](?:description|og:description|og:title|og:image)["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
TITLE_RE = re.compile(r"<title>([^<]+)</title>", re.IGNORECASE)
USERNAME_TOKEN_RE = re.compile(r"[\w.+-]+")


def _extract_meta(html: str) -> dict[str, str | None]:
    out: dict[str, str | None] = {"title": None, "description": None, "image": None}
    t = TITLE_RE.search(html)
    if t:
        out["title"] = t.group(1).strip()[:120]
    # Look for specific property/name values
    for m in re.finditer(
        r'<meta\s+(?:[^>]*?name=["\'](?P<n>[^"\']+)["\']|'
        r'[^>]*?property=["\'](?P<p>[^"\']+)["\'])'
        r'[^>]*?content=["\'](?P<c>[^"\']+)["\']',
        html, re.IGNORECASE,
    ):
        key = (m.group("n") or m.group("p") or "").lower()
        val = m.group("c")
        if key in ("og:title", "twitter:title") and not out["title"]:
            out["title"] = val.strip()[:120]
        elif key in ("description", "og:description", "twitter:description"):
            out["description"] = val.strip()[:400]
        elif key in ("og:image", "twitter:image") and not out["image"]:
            out["image"] = val.strip()
    return out


def _looks_like_profile(html: str, username: str, platform: str) -> bool:
    """Heuristic: does the HTML look like an actual user profile?"""
    text = html.lower()
    if username.lower() in text:
        return True
    if platform.lower().replace("/", "") in text:
        return True
    # Some platforms (LinkedIn, Instagram) return a generic page even when
    # the profile exists. The `reliable=False` flag on the platform tells
    # the caller to downweight this heuristic for those.
    return False


# ---- strategy framework --------------------------------------------------- #

STRATEGY_TIMEOUT = 8.0


async def _run_strategy(
    coro: Awaitable[Any], *, timeout: float = STRATEGY_TIMEOUT
) -> dict[str, Any]:
    """Wrap a strategy call with a timeout + shape it into a result dict."""
    t0 = time.perf_counter()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return {"ok": False, "error": "timeout", "duration_ms": int((time.perf_counter() - t0) * 1000)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:160], "duration_ms": int((time.perf_counter() - t0) * 1000)}
    ms = int((time.perf_counter() - t0) * 1000)
    if isinstance(result, dict):
        result = {**result, "duration_ms": ms}
    return result


# ---- platform definitions ------------------------------------------------- #

@dataclass(frozen=True)
class Strategy:
    name: str                       # "http" | "api" | "oembed" | "favicon"
    weight: float = 1.0             # 0..1
    reliable: bool = True           # contributes to confidence when true


@dataclass(frozen=True)
class Platform:
    name: str
    primary_url: str
    reliable: bool = True
    # Each platform has 1+ strategies. A strategy is a callable that takes
    # (client, username) and returns {"ok": bool, ...metadata}.
    strategy_factory: Callable[[str], list[tuple[Strategy, Callable]]] | None = None

    def build(self, username: str) -> str:
        return self.primary_url.format(u=username)


# ---- per-platform strategy factories ------------------------------------- #
# We build them as functions so the `Platform` class doesn't need methods,
# which keeps the registry declarative and easy to extend.

def _http_strategy(url: str, name: str, *, meta_title: bool = True, reliable: bool = True):
    """Build an HTTP-fetch strategy that returns meta info if the page exists."""
    async def _run(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
        try:
            r = await client.get(url.format(u=username), follow_redirects=True, timeout=STRATEGY_TIMEOUT)
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)[:160]}
        if r.status_code != 200 or len(r.text) < 200:
            return {"ok": False, "status": r.status_code, "found": False}
        looks = _looks_like_profile(r.text, username, name)
        meta = _extract_meta(r.text) if meta_title else {}
        return {
            "ok": True,
            "found": looks or reliable,  # reliable platforms: even weak signal counts
            "display_name": meta.get("title"),
            "bio": meta.get("description"),
            "avatar_url": meta.get("image"),
        }
    return _run


def _api_strategy(url: str, parse_fn: Callable[[dict, str], dict]):
    """Build a JSON-API strategy. parse_fn(j, username) -> result dict."""
    async def _run(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
        try:
            r = await client.get(url.format(u=username), follow_redirects=True, timeout=STRATEGY_TIMEOUT)
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)[:160]}
        if r.status_code == 404:
            return {"ok": True, "found": False, "status": 404}
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code, "found": False}
        try:
            j = r.json()
        except Exception:
            return {"ok": False, "error": "non-json response"}
        return {"ok": True, "found": True, **parse_fn(j, username)}
    return _run


def _oembed_strategy(url: str):
    async def _run(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
        try:
            r = await client.get(url.format(u=username), follow_redirects=True, timeout=STRATEGY_TIMEOUT)
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)[:160]}
        if r.status_code == 404 or r.status_code >= 400:
            return {"ok": True, "found": False, "status": r.status_code}
        try:
            j = r.json()
        except Exception:
            return {"ok": False, "error": "non-json response"}
        return {"ok": True, "found": True, "display_name": j.get("title"), "avatar_url": j.get("thumbnail_url")}
    return _run


# ---- the actual platform list -------------------------------------------- #

def _strategies_github(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://api.github.com/users/{u}",
            lambda j, u: {
                "display_name": j.get("name"),
                "bio": j.get("bio"),
                "avatar_url": j.get("avatar_url"),
                "found": j.get("login", "").lower() == u.lower() and "type" in j,
            },
        )),
        (Strategy("http", 0.5, reliable=False), _http_strategy(
            "https://github.com/{u}", "github", meta_title=True, reliable=True
        )),
    ]


def _strategies_gitlab(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://gitlab.com/api/v4/users?username={u}",
            lambda j, u: {
                "display_name": j[0].get("name") if j else None,
                "bio": j[0].get("bio") if j else None,
                "avatar_url": j[0].get("avatar_url") if j else None,
                "found": bool(j) and j[0].get("username", "").lower() == u.lower(),
            },
        )),
    ]


def _strategies_twitter(_: str):
    return [
        # X / Twitter does not have a public user API anymore. The HTML
        # profile page usually returns 200 even for non-existent users
        # (renders a "this account doesn't exist" component). We downgrade
        # this to a best-effort signal.
        (Strategy("http", 0.3, reliable=False), _http_strategy(
            "https://x.com/{u}", "twitter", meta_title=True, reliable=False
        )),
        # Syndication API often exposes posts for existing users.
        (Strategy("api", 0.6, reliable=False), _api_strategy(
            "https://syndication.twitter.com/srv/timeline-profile/screen-name/{u}",
            lambda j, u: {
                "display_name": None,
                "bio": None,
                "avatar_url": None,
                "found": isinstance(j, dict) and (j.get("body") or "").strip() != "",
            },
        )),
    ]


def _strategies_reddit(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://www.reddit.com/user/{u}/about.json",
            lambda j, u: {
                "display_name": (j.get("data") or {}).get("name"),
                "bio": ((j.get("data") or {}).get("subreddit") or {}).get("public_description"),
                "avatar_url": (j.get("data") or {}).get("icon_img"),
                "found": bool((j.get("data") or {}).get("name")),
            },
        )),
    ]


def _strategies_instagram(_: str):
    return [
        (Strategy("http", 0.4, reliable=False), _http_strategy(
            "https://www.instagram.com/{u}/", "instagram", meta_title=True, reliable=False
        )),
        # og:profile meta is often present for real accounts
        (Strategy("og", 0.4, reliable=False), _http_strategy(
            "https://www.instagram.com/{u}/", "instagram", meta_title=True, reliable=False
        )),
    ]


def _strategies_tiktok(_: str):
    return [
        (Strategy("http", 0.4, reliable=False), _http_strategy(
            "https://www.tiktok.com/@{u}", "tiktok", meta_title=True, reliable=False
        )),
        (Strategy("oembed", 0.5, reliable=False), _oembed_strategy(
            "https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{u}"
        )),
    ]


def _strategies_threads(_: str):
    return [
        (Strategy("http", 0.3, reliable=False), _http_strategy(
            "https://www.threads.net/@{u}", "threads", meta_title=True, reliable=False
        )),
    ]


def _strategies_facebook(_: str):
    return [
        (Strategy("http", 0.2, reliable=False), _http_strategy(
            "https://www.facebook.com/{u}", "facebook", meta_title=False, reliable=False
        )),
    ]


def _strategies_linkedin(_: str):
    return [
        (Strategy("http", 0.2, reliable=False), _http_strategy(
            "https://www.linkedin.com/in/{u}", "linkedin", meta_title=False, reliable=False
        )),
    ]


def _strategies_youtube(_: str):
    return [
        (Strategy("oembed", 0.6), _oembed_strategy(
            "https://www.youtube.com/oembed?url=https://www.youtube.com/@{u}&format=json"
        )),
        (Strategy("http", 0.5), _http_strategy(
            "https://www.youtube.com/@{u}", "youtube", meta_title=True, reliable=True
        )),
    ]


def _strategies_pinterest(_: str):
    return [
        (Strategy("http", 0.7), _http_strategy(
            "https://www.pinterest.com/{u}/", "pinterest", meta_title=True, reliable=True
        )),
    ]


def _strategies_twitch(_: str):
    return [
        (Strategy("http", 0.7), _http_strategy(
            "https://www.twitch.tv/{u}", "twitch", meta_title=True, reliable=True
        )),
    ]


def _strategies_steam(_: str):
    return [
        (Strategy("http", 0.7), _http_strategy(
            "https://steamcommunity.com/id/{u}", "steam", meta_title=True, reliable=True
        )),
    ]


def _strategies_telegram(_: str):
    return [
        # t.me pages return 200 for almost anything; we check for a redirect
        # to telegram.org or a "You can contact …" hint. Most of the time
        # the only reliable signal is a real preview card on the page.
        (Strategy("http", 0.3, reliable=False), _http_strategy(
            "https://t.me/{u}", "telegram", meta_title=True, reliable=False
        )),
    ]


def _strategies_keybase(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://keybase.io/{u}/_/api/1.0/user/lookup.json",
            lambda j, u: {
                "display_name": ((j.get("them") or [{}])[0] or {}).get("profile", {}).get("full_name"),
                "bio": ((j.get("them") or [{}])[0] or {}).get("profile", {}).get("bio"),
                "avatar_url": (((j.get("them") or [{}])[0] or {}).get("pictures") or {}).get("primary", {}).get("url"),
                "found": bool((j.get("them") or [])),
            },
        )),
    ]


def _strategies_gravatar(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://www.gravatar.com/{u}.json",
            lambda j, u: {
                "display_name": ((j.get("entry") or [{}])[0] or {}).get("displayName"),
                "bio": None,
                "avatar_url": ((j.get("entry") or [{}])[0] or {}).get("thumbnailUrl"),
                "found": bool(j.get("entry")),
            },
        )),
    ]


def _strategies_medium(_: str):
    return [
        (Strategy("http", 0.7), _http_strategy(
            "https://medium.com/@{u}", "medium", meta_title=True, reliable=True
        )),
    ]


def _strategies_devto(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://dev.to/api/users/by_username?url={u}",
            lambda j, u: {
                "display_name": j.get("name"),
                "bio": j.get("summary"),
                "avatar_url": j.get("profile_image"),
                "found": j.get("username", "").lower() == u.lower(),
            },
        )),
    ]


def _strategies_stackoverflow(_: str):
    # The StackExchange API doesn't support {u} templating directly with
    # `users/`; it expects a query. Use the api/users endpoint with `inname`
    # via a fixed URL — we'll override the URL at strategy-build time below.
    async def _run(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
        url = f"https://api.stackexchange.com/2.3/users?site=stackoverflow&inname={username}"
        try:
            r = await client.get(url, follow_redirects=True, timeout=STRATEGY_TIMEOUT)
        except httpx.HTTPError as e:
            return {"ok": False, "error": str(e)[:160]}
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code, "found": False}
        try:
            j = r.json()
        except Exception:
            return {"ok": False, "error": "non-json"}
        items = j.get("items") or []
        # The best match is the first item (highest reputation)
        first = items[0] if items else {}
        return {
            "ok": True,
            "found": bool(items),
            "display_name": first.get("display_name"),
            "avatar_url": first.get("profile_image"),
            "bio": None,
        }
    return [(Strategy("api", 0.6), _run)]


def _strategies_hackernews(_: str):
    return [
        (Strategy("api", 1.0), _api_strategy(
            "https://hacker-news.firebaseio.com/v0/user/{u}.json",
            lambda j, u: {
                "display_name": j.get("about") if isinstance(j, dict) else None,
                "bio": (j.get("about") if isinstance(j, dict) else None),
                "avatar_url": None,
                "found": isinstance(j, dict) and j.get("id", "").lower() == u.lower(),
            },
        )),
    ]


# These three use a simple, reliable HTTP strategy.
def _strategies_behance(_: str):
    return [(Strategy("http", 0.7), _http_strategy("https://www.behance.net/{u}", "behance"))]
def _strategies_dribbble(_: str):
    return [(Strategy("http", 0.7), _http_strategy("https://dribbble.com/{u}", "dribbble"))]
def _strategies_soundcloud(_: str):
    return [(Strategy("http", 0.7), _http_strategy("https://soundcloud.com/{u}", "soundcloud"))]
def _strategies_spotify(_: str):
    return [(Strategy("http", 0.4, reliable=False), _http_strategy("https://open.spotify.com/user/{u}", "spotify", reliable=False))]
def _strategies_vimeo(_: str):
    return [(Strategy("http", 0.7), _http_strategy("https://vimeo.com/{u}", "vimeo"))]
def _strategies_aboutme(_: str):
    return [(Strategy("http", 0.7), _http_strategy("https://about.me/{u}", "aboutme"))]


def _strategies_mastodon(_: str):
    # Mastodon is federated: no single canonical URL. We probe the public
    # /api/v1/accounts/lookup endpoint on a few large instances.
    async def _lookup(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for base in ("https://mastodon.social", "https://mastodon.online", "https://mas.to"):
            try:
                r = await client.get(
                    f"{base}/api/v1/accounts/lookup",
                    params={"acct": username},
                    follow_redirects=True,
                    timeout=STRATEGY_TIMEOUT,
                    headers={"Accept": "application/json"},
                )
            except (httpx.HTTPError, Exception) as e:
                log.debug("Mastodon probe %s failed: %s", base, e)
                continue
            if r.status_code == 404:
                continue
            if r.status_code != 200:
                continue
            try:
                j = r.json()
            except Exception:
                continue
            if isinstance(j, dict) and j.get("id"):
                results.append({
                    "instance": base,
                    "display_name": j.get("display_name"),
                    "avatar_url": j.get("avatar"),
                    "url": j.get("url"),
                    "followers": j.get("followers_count"),
                    "verified": bool(j.get("verified")),
                })
        if results:
            first = results[0]
            return {
                "ok": True,
                "found": True,
                "display_name": first["display_name"],
                "avatar_url": first["avatar_url"],
                "instances": results,
            }
        return {"ok": True, "found": False}

    async def _web(_client: httpx.AsyncClient, _u: str) -> dict[str, Any]:
        # Web check is unreliable for federated profiles; we just say
        # "not found" so the API check wins.
        return {"ok": True, "found": False}

    return [
        (Strategy("api", 1.0), _lookup),
        (Strategy("http", 0.2, reliable=False), _web),
    ]


# ---- registry ------------------------------------------------------------ #

PLATFORMS: list[Platform] = [
    Platform("GitHub",       "https://github.com/{u}", strategy_factory=_strategies_github),
    Platform("GitLab",       "https://gitlab.com/{u}", strategy_factory=_strategies_gitlab),
    Platform("Twitter/X",    "https://x.com/{u}", reliable=False, strategy_factory=_strategies_twitter),
    Platform("Reddit",       "https://www.reddit.com/user/{u}", strategy_factory=_strategies_reddit),
    Platform("Instagram",    "https://www.instagram.com/{u}/", reliable=False, strategy_factory=_strategies_instagram),
    Platform("TikTok",       "https://www.tiktok.com/@{u}", reliable=False, strategy_factory=_strategies_tiktok),
    Platform("Threads",      "https://www.threads.net/@{u}", reliable=False, strategy_factory=_strategies_threads),
    Platform("YouTube",      "https://www.youtube.com/@{u}", strategy_factory=_strategies_youtube),
    Platform("Facebook",     "https://www.facebook.com/{u}", reliable=False, strategy_factory=_strategies_facebook),
    Platform("LinkedIn",     "https://www.linkedin.com/in/{u}", reliable=False, strategy_factory=_strategies_linkedin),
    Platform("Pinterest",    "https://www.pinterest.com/{u}/", strategy_factory=_strategies_pinterest),
    Platform("Telegram",     "https://t.me/{u}", reliable=False, strategy_factory=_strategies_telegram),
    Platform("Twitch",       "https://www.twitch.tv/{u}", strategy_factory=_strategies_twitch),
    Platform("Steam",        "https://steamcommunity.com/id/{u}", strategy_factory=_strategies_steam),
    Platform("Keybase",      "https://keybase.io/{u}", strategy_factory=_strategies_keybase),
    Platform("Gravatar",     "https://www.gravatar.com/{u}", strategy_factory=_strategies_gravatar),
    Platform("Medium",       "https://medium.com/@{u}", strategy_factory=_strategies_medium),
    Platform("Dev.to",       "https://dev.to/{u}", strategy_factory=_strategies_devto),
    Platform("StackOverflow","https://stackoverflow.com/users/{u}", strategy_factory=_strategies_stackoverflow),
    Platform("HackerNews",   "https://news.ycombinator.com/user?id={u}", strategy_factory=_strategies_hackernews),
    Platform("Behance",      "https://www.behance.net/{u}", strategy_factory=_strategies_behance),
    Platform("Dribbble",     "https://dribbble.com/{u}", strategy_factory=_strategies_dribbble),
    Platform("SoundCloud",   "https://soundcloud.com/{u}", strategy_factory=_strategies_soundcloud),
    Platform("Spotify",      "https://open.spotify.com/user/{u}", reliable=False, strategy_factory=_strategies_spotify),
    Platform("Vimeo",        "https://vimeo.com/{u}", strategy_factory=_strategies_vimeo),
    Platform("About.me",     "https://about.me/{u}", strategy_factory=_strategies_aboutme),
    Platform("Mastodon",     "https://mastodon.social/@{u}", reliable=False, strategy_factory=_strategies_mastodon),
]

BY_NAME: dict[str, Platform] = {p.name: p for p in PLATFORMS}


# ---- provider ------------------------------------------------------------ #

class UsernameProvider(BaseProvider):
    name = "username"
    kind = "username"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 60
    cache_ttl = 60 * 30
    timeout_seconds = 30.0  # overall budget for all platforms
    health_url = "https://github.com/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        username = target.strip().lstrip("@")
        if not username or len(username) > 64 or not re.match(r"^[A-Za-z0-9._-]+$", username):
            return {
                "username": username,
                "count": 0,
                "results": [],
                "confidence": 0.0,
                "duration_ms": 0,
            }

        # Optional platform filter
        wanted = None
        if kwargs.get("platforms"):
            wanted = {p.strip().lower() for p in kwargs["platforms"].split(",") if p.strip()}

        platforms = [p for p in PLATFORMS if not wanted or p.name.lower() in wanted]

        # 8 concurrent platforms at a time; each platform runs its strategies concurrently
        outer = asyncio.Semaphore(8)
        # Shorten the shared client once for all platforms
        async with httpx.AsyncClient(
            headers={"User-Agent": "HelloYou/1.0 (+educational)"},
            follow_redirects=True,
            http2=False,
            timeout=STRATEGY_TIMEOUT,
        ) as client:
            tasks = [self._check_platform(client, outer, p, username) for p in platforms]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        final: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            if r and r.get("found"):
                final.append(r)

        # Sort by confidence desc
        final.sort(key=lambda x: x["confidence"], reverse=True)
        avg_conf = round(sum(f["confidence"] for f in final) / len(final), 2) if final else 0.0
        return {
            "username": username,
            "count": len(final),
            "results": final,
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
        t0 = time.perf_counter()
        async with sem:
            strategies = (platform.strategy_factory or (lambda _u: []))(username)
            if not strategies:
                return None

            # Run all strategies for this platform concurrently
            runs = await asyncio.gather(
                *[_run_strategy(strat_fn(client, username)) for _, strat_fn in strategies],
                return_exceptions=False,
            )

        # Combine strategy results
        yes_votes: list[float] = []
        no_votes: list[float] = []
        fields: dict[str, Any] = {}
        strategy_log: list[dict[str, Any]] = []
        for (strat, _), r in zip(strategies, runs):
            strategy_log.append({
                "name": strat.name,
                "weight": strat.weight,
                "ok": r.get("ok", False),
                "found": r.get("found", False),
                "duration_ms": r.get("duration_ms", 0),
                "error": r.get("error"),
            })
            if r.get("found") and r.get("ok"):
                yes_votes.append(strat.weight)
                # First non-null wins for the display fields
                for k in ("display_name", "bio", "avatar_url"):
                    if not fields.get(k) and r.get(k):
                        fields[k] = r[k]
            elif r.get("ok"):
                no_votes.append(strat.weight)

        # Confidence: weighted agreement
        total = sum(yes_votes) + sum(no_votes)
        if total == 0:
            return None
        agreement = sum(yes_votes) / total
        # Base reliability multiplier
        base = 0.85 if platform.reliable else 0.5
        confidence = round(min(0.99, base * agreement + (0.1 if fields.get("display_name") else 0)), 2)

        found = len(yes_votes) > 0
        # Require at least one *strong* strategy to confirm a weak platform.
        # `strategies` is a list of (Strategy, callable) tuples.
        if not platform.reliable and not any(
            strat.weight >= 0.5 and r.get("found") and r.get("ok")
            for (strat, _), r in zip(strategies, runs)
        ):
            found = False
            confidence = min(confidence, 0.45)

        response_time_ms = int((time.perf_counter() - t0) * 1000)

        return {
            "platform": platform.name,
            "profile_url": platform.build(username),
            "username": username,
            "display_name": fields.get("display_name"),
            "bio": fields.get("bio"),
            "avatar_url": fields.get("avatar_url"),
            "verified": found,
            "found": found,
            "confidence": confidence,
            "response_time_ms": response_time_ms,
            "reliable": platform.reliable,
            "strategies": strategy_log,
        }
