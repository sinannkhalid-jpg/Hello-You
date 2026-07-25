"""
Helpers used by the username provider's per-platform checkers.

Every checker returns a `dict` with these fields (all optional except
`ok` and `found`):

    ok      : bool   — the request itself completed successfully
    found   : bool   — the platform reported the username exists
    display_name : str | None
    bio           : str | None
    avatar_url    : str | None
    extra         : dict

Most platforms use one of these patterns:

  1. Public unauthenticated JSON API (strongest signal, high weight).
  2. oEmbed endpoint (strong; returns 200 only for real profiles).
  3. HTML profile page — distinguished from a 404 by:
       • the page title (e.g. "VimeUhOh" = missing on Vimeo)
       • page size threshold (missing pages are noticeably smaller)
       • og:title / og:image meta tags
  4. Syndication endpoints (e.g. Twitter syndication).

The checkers below are intentionally tolerant of layout changes:
they treat anything ambiguous as "not found" rather than returning a
false positive.
"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote

import httpx

# ---------- HTML / meta parsing ------------------------------------------------

_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)
_OG_RE = re.compile(
    r'<meta\s+[^>]*?(?:name|property)\s*=\s*["\']([a-zA-Z:-]+)["\']\s+[^>]*?content\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def parse_meta(html: str) -> dict[str, str]:
    """Return all (name|property) → content meta tag pairs as a dict."""
    out: dict[str, str] = {}
    for m in _OG_RE.finditer(html):
        key = (m.group(1) or "").lower()
        val = m.group(2) or ""
        if val and key not in out:
            out[key] = val[:500]
    return out


def title_of(html: str) -> str | None:
    m = _TITLE_RE.search(html)
    if not m:
        return None
    t = m.group(1).strip()
    return t[:160] if t else None


def pick_avatar(meta: dict[str, str]) -> str | None:
    for k in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"):
        v = meta.get(k)
        if v and v.startswith("http"):
            return v
    return None


def pick_display_name(meta: dict[str, str], title: str | None, fallback: str) -> str:
    for k in ("og:title", "twitter:title"):
        v = meta.get(k)
        if v:
            # Strip a "(@username) | platform" suffix to keep just the name
            return v.split("|")[0].strip().split("(")[0].strip() or fallback
    if title:
        # Many sites put the username in the title when there's no display
        # name, so keep the title as-is
        return title
    return fallback


# ---------- HTTP helpers -------------------------------------------------------

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _client_headers(extra: dict | None = None) -> dict[str, str]:
    h = {
        "User-Agent": DEFAULT_UA,
        "Accept": "application/json, text/html;q=0.9, */*;q=0.5",
        "Accept-Language": "en-US,en;q=0.7",
    }
    if extra:
        h.update({k: v for k, v in extra.items() if v is not None})
    return h


async def safe_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict | None = None,
    timeout: float = 8.0,
) -> httpx.Response | None:
    """GET with the default browser headers; returns None on network error."""
    try:
        return await client.get(
            url,
            headers=_client_headers(headers),
            follow_redirects=True,
            timeout=timeout,
        )
    except (httpx.HTTPError, Exception):
        return None


# ---------- Generic HTML page checker -----------------------------------------

# Pages that have a reliable "missing" title on the platform's domain.
_KNOWN_MISSING_TITLES = {
    "github":     ["page not found", "404 not found"],
    "gitlab":     ["page not found"],
    "bitbucket":  ["page not found", "bitbucket cloud"],
    "vimeo":      ["vimeuhoh"],
    "behance":    ["oops! we can’t find that page", "oops! we can't find that page"],
    "dribbble":   ["page not found", "not found"],
    "linkedin":   ["page not found"],
    "medium":     [],  # Cloudflare challenge, can't use
    "youtube":    ["404 not found"],
    "twitch":     [],
    "spotify":    [],
    "snapchat":   [],
    "pinterest":  [],
    "mastodon":   [],
    "facebook":   ["log into facebook"],
    "telegram":   [],
    "twitter":    ["this account doesn’t exist", "this account doesn't exist"],
    "tiktok":     [],
    "instagram":  ["page not found"],
    "threads":    [],
    "dev.to":     ["page not found"],
    "soundcloud": ["page not found"],
    "stackoverflow": ["page not found"],
    "hackernews": [],
    "aboutme":    [],
    "vimeo":      ["vimeuhoh"],
    "reddit":     ["page not found"],
    "steam":      ["steam community :: error"],
    "keybase":    ["page not found"],
    "gravatar":   ["page not found"],
}


async def html_check(
    client: httpx.AsyncClient,
    url: str,
    *,
    platform_key: str,
    min_size: int = 500,
    success_size: int = 0,
    not_found_markers: tuple[str, ...] = (),
    not_found_title_markers: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Generic HTML existence checker.

    Returns {"ok", "found", "html", "size", "status"}.

    The "found" decision is:
      • HTTP 200 AND size > min_size AND no not_found marker
      • AND title does not contain a known "missing" string for this platform
    """
    r = await safe_get(client, url)
    if r is None:
        return {"ok": False, "found": False, "error": "request failed"}
    if r.status_code >= 400:
        # Many platforms return 404 directly for missing users
        return {"ok": True, "found": False, "status": r.status_code}
    text = r.text or ""
    size = len(text)
    if size < min_size:
        return {"ok": True, "found": False, "status": r.status_code, "size": size}

    found = True
    text_lower = text.lower()
    for marker in not_found_markers:
        if marker.lower() in text_lower:
            found = False
            break

    if found:
        title = title_of(text) or ""
        title_lower = title.lower()
        for marker in not_found_title_markers:
            if marker.lower() in title_lower:
                found = False
                break
        for marker in _KNOWN_MISSING_TITLES.get(platform_key, []):
            if marker in title_lower:
                found = False
                break

    # Some platforms (Snapchat, X) return 200 for both, but real users
    # have a much larger page. Use the size threshold as a tiebreaker.
    if found and success_size and size < success_size:
        found = False

    return {
        "ok": True,
        "found": found,
        "status": r.status_code,
        "size": size,
        "html": text,
    }


# ---------- Specialized checkers (one per platform) ---------------------------

async def check_github(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(
        client, f"https://api.github.com/users/{username}",
        headers={"Accept": "application/vnd.github+json"},
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False, "status": r.status_code if r else None}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    if not isinstance(j, dict) or j.get("message"):
        return {"ok": True, "found": False}
    return {
        "ok": True,
        "found": True,
        "display_name": j.get("name") or j.get("login"),
        "bio": j.get("bio"),
        "avatar_url": j.get("avatar_url"),
        "extra": {
            "id": j.get("id"),
            "type": j.get("type"),
            "company": j.get("company"),
            "location": j.get("location"),
            "public_repos": j.get("public_repos"),
            "followers": j.get("followers"),
        },
    }


async def check_gitlab(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """GitLab: API returns [] for missing, [user] for existing."""
    r = await safe_get(client, f"https://gitlab.com/api/v4/users?username={username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        arr = r.json()
    except Exception:
        return {"ok": True, "found": False}
    if not isinstance(arr, list) or not arr:
        return {"ok": True, "found": False}
    u = arr[0]
    if not isinstance(u, dict):
        return {"ok": True, "found": False}
    return {
        "ok": True,
        "found": str(u.get("username", "")).lower() == username.lower(),
        "display_name": u.get("name"),
        "bio": u.get("bio"),
        "avatar_url": u.get("avatar_url"),
        "extra": {"id": u.get("id"), "public_repos": u.get("public_repos")},
    }


async def check_bitbucket(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://api.bitbucket.org/2.0/users/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    if not isinstance(j, dict) or "error" in j:
        return {"ok": True, "found": False}
    links = j.get("links", {}) or {}
    avatar = (links.get("avatar") or {}).get("href")
    return {
        "ok": True,
        "found": True,
        "display_name": j.get("display_name") or j.get("username"),
        "avatar_url": avatar,
        "extra": {"uuid": j.get("uuid"), "type": j.get("type")},
    }


async def check_reddit(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Reddit blocks most anonymous access at the network level
    (returns 301 to login or 403 'Blocked' page). We try the JSON API
    with a descriptive User-Agent; if we get anything other than 200/404,
    we report it as 'unavailable' so the orchestrator doesn't keep
    trying."""
    r = await safe_get(
        client,
        f"https://www.reddit.com/user/{username}/about.json",
        headers={"User-Agent": DEFAULT_UA},
    )
    if r is None:
        return {"ok": False, "found": False, "error": "request failed"}
    if r.status_code == 404:
        return {"ok": True, "found": False, "status": 404}
    if r.status_code == 301:
        return {"ok": True, "found": None,
                "extra": {"reason": "login_required"}}
    if r.status_code != 200:
        return {"ok": True, "found": None, "status": r.status_code,
                "extra": {"reason": "blocked"}}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": None, "extra": {"reason": "non_json"}}
    data = (j or {}).get("data") or {}
    if not data or data.get("name", "").lower() != username.lower():
        return {"ok": True, "found": False}
    sub = data.get("subreddit") or {}
    return {
        "ok": True,
        "found": True,
        "display_name": data.get("name"),
        "bio": sub.get("public_description") if isinstance(sub, dict) else None,
        "avatar_url": data.get("icon_img"),
        "extra": {"link_karma": data.get("link_karma"), "comment_karma": data.get("comment_karma")},
    }


async def check_steam(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Steam: /id/{u}?xml=1 returns a small XML for missing, larger for real."""
    r = await safe_get(
        client, f"https://steamcommunity.com/id/{username}?xml=1",
        timeout=8.0,
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    if "<error>" in text or "could not be found" in text.lower():
        return {"ok": True, "found": False}
    if "<steamID64>" not in text:
        return {"ok": True, "found": False}
    # Pull display name from the HTML title for the avatar URL
    html = await safe_get(client, f"https://steamcommunity.com/id/{username}")
    avatar = None
    display = username
    if html is not None and html.status_code == 200:
        m = re.search(
            r'<title>Steam Community :: ([^<]+)</title>',
            html.text or "", re.IGNORECASE,
        )
        if m:
            display = m.group(1).strip() or display
        am = re.search(
            r'<link rel="image_src" href="([^"]+)"',
            html.text or "",
        )
        if am:
            avatar = am.group(1)
    return {
        "ok": True, "found": True,
        "display_name": display,
        "profile_url": f"https://steamcommunity.com/id/{username}",
        "avatar_url": avatar,
    }


async def check_keybase(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(
        client, f"https://keybase.io/{username}/_/api/1.0/user/lookup.json",
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    them = (j or {}).get("them") or []
    if not them:
        return {"ok": True, "found": False}
    profile = (them[0] or {}).get("profile") or {}
    pictures = (them[0] or {}).get("pictures") or {}
    primary = pictures.get("primary") or {}
    return {
        "ok": True, "found": True,
        "display_name": profile.get("full_name"),
        "bio": profile.get("bio"),
        "avatar_url": primary.get("url"),
    }


async def check_gravatar(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://www.gravatar.com/{username}.json")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    entries = (j or {}).get("entry") or []
    if not entries:
        return {"ok": True, "found": False}
    e = entries[0] or {}
    profile = e.get("profile") or {}
    return {
        "ok": True, "found": True,
        "display_name": e.get("displayName") or profile.get("displayName"),
        "avatar_url": (e.get("thumbnailUrl") or
                       (e.get("photos") or [{}])[0].get("value")),
    }


async def check_twitter_x(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """X / Twitter: HTML page is JS-rendered. The size signature is the
    most reliable non-API signal: real-profile pages are ~55KB, the
    "doesn't exist" page is ~265KB."""
    r = await safe_get(client, f"https://x.com/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    size = len(r.text or "")
    title = title_of(r.text or "") or ""
    if "suspend" in title.lower() or "doesn’t exist" in title.lower() or \
       "doesn't exist" in title.lower():
        return {"ok": True, "found": False, "status": r.status_code}
    if size > 100_000:  # large page = missing
        return {"ok": True, "found": False, "status": r.status_code, "size": size}
    return {
        "ok": True, "found": True, "status": r.status_code, "size": size,
        "display_name": None,
        "extra": {"title": title},
    }


async def check_facebook(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Facebook: real users get 200 + 400KB+ page + a real title.
    Missing users get redirected to login (302). Facebook returns 400
    when the Accept header is not text/html-friendly, so we set
    Accept: text/html explicitly."""
    r = await safe_get(
        client, f"https://www.facebook.com/{username}",
        headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    if r is None:
        return {"ok": False, "found": False}
    if r.status_code in (302, 303):
        return {"ok": True, "found": False, "status": r.status_code}
    if r.status_code != 200:
        return {"ok": True, "found": False, "status": r.status_code}
    text = r.text or ""
    if len(text) < 50_000:
        return {"ok": True, "found": False, "size": len(text)}
    title = title_of(text) or ""
    if title.lower().strip() in ("facebook", "facebook - log in", "log in to facebook"):
        return {"ok": True, "found": False}
    meta = parse_meta(text)
    display = pick_display_name(meta, title, username)
    return {
        "ok": True, "found": True,
        "display_name": display,
        "avatar_url": pick_avatar(meta),
        "extra": {"title": title},
    }


async def check_instagram(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Instagram's public web profile API.

    URL: https://www.instagram.com/api/v1/users/web_profile_info/?username=<u>
    Header: x-ig-app-id: 936619743392459 (public, documented)
        real user: 200 + ~165KB JSON with user.biography, profile_pic_url, etc.
        missing:   404 + ~21KB

    The HTML page is locked behind a login wall (302 → login), so the
    API is the only viable anonymous check.
    """
    r = await safe_get(
        client,
        f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
        headers={"x-ig-app-id": "936619743392459"},
    )
    if r is None or r.status_code == 404:
        return {"ok": r is not None, "found": False, "status": r.status_code if r else None}
    if r.status_code != 200:
        return {"ok": True, "found": False, "status": r.status_code}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    user = (j or {}).get("data", {}).get("user") or {}
    if not user:
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": user.get("full_name") or user.get("username"),
        "bio": user.get("biography"),
        "avatar_url": user.get("profile_pic_url"),
        "extra": {
            "follower_count": user.get("follower_count"),
            "following_count": user.get("following_count"),
            "is_verified": user.get("is_verified"),
            "is_private": user.get("is_private"),
        },
    }


async def check_threads(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Threads uses Instagram's public web_profile_info API."""
    r = await safe_get(
        client,
        f"https://www.threads.net/api/v1/users/web_profile_info/?username={username}",
        headers={"x-ig-app-id": "936619743392459"},
    )
    if r is None or r.status_code == 404:
        return {"ok": r is not None, "found": False, "status": r.status_code if r else None}
    if r.status_code != 200:
        return {"ok": True, "found": False, "status": r.status_code}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    user = (j or {}).get("data", {}).get("user") or {}
    if not user:
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": user.get("full_name") or user.get("username"),
        "bio": user.get("biography"),
        "avatar_url": user.get("profile_pic_url"),
        "extra": {"follower_count": user.get("follower_count")},
    }


async def check_tiktok(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """TikTok's oEmbed endpoint returns 200 with JSON for real users and
    400 with {"message":"Something went wrong"} for missing users."""
    r = await safe_get(
        client, "https://www.tiktok.com/oembed",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # oembed requires the URL as a query parameter, not just a path
    r = await safe_get(
        client,
        f"https://www.tiktok.com/oembed?url=https://www.tiktok.com/@{username}",
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    if not isinstance(j, dict) or j.get("code") or j.get("error"):
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": j.get("author_name"),
        "profile_url": j.get("author_url"),
        "avatar_url": j.get("thumbnail_url"),
    }


async def check_youtube(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """YouTube's oEmbed endpoint is unreliable. Instead we hit the
    /@handle HTML page directly:
        real user: 200 + body > 800KB + title contains the user name
        missing:   404 + body < 1KB + title is "404 Not Found"
    """
    r = await safe_get(client, f"https://www.youtube.com/@{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False, "status": r.status_code if r else None}
    text = r.text or ""
    size = len(text)
    if size < 50_000:
        return {"ok": True, "found": False, "status": r.status_code, "size": size}
    title = title_of(text) or ""
    if "404" in title or "Not Found" in title:
        return {"ok": True, "found": False}
    meta = parse_meta(text)
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(meta, title, username),
        "avatar_url": pick_avatar(meta),
        "extra": {"title": title, "size": size},
    }


async def check_linkedin(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """LinkedIn returns 200 for real users, 999 for missing, 302 for redirect."""
    r = await safe_get(client, f"https://www.linkedin.com/in/{username}")
    if r is None:
        return {"ok": False, "found": False}
    if r.status_code == 999 or r.status_code == 404:
        return {"ok": True, "found": False, "status": r.status_code}
    if r.status_code == 200 and len(r.text or "") > 50_000:
        text = r.text or ""
        title = title_of(text) or ""
        meta = parse_meta(text)
        display = pick_display_name(meta, title, username)
        return {
            "ok": True, "found": True,
            "display_name": display,
            "avatar_url": pick_avatar(meta),
            "extra": {"title": title},
        }
    return {"ok": True, "found": False, "status": r.status_code}


async def check_twitch(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Twitch's public oEmbed endpoint is dead and the web profile is
    fully JS-rendered (identical 192KB for real and missing users).

    The reliable third-party endpoint is decapi.me (a community Twitch
    API), which returns a numeric ID for real users and "User not
    found: <name>" for missing ones. We also try the public Twitch
    GraphQL `UseLive` query — it returns a user object (with id) for
    channels that have ever streamed, and null for users that have
    never streamed or don't exist.

    The decapi.me check is the authoritative one.
    """
    # 1) decapi.me lookup
    r = await safe_get(
        client,
        f"https://decapi.me/twitch/id/{username}",
        timeout=6.0,
    )
    if r is not None and r.status_code == 200:
        text = (r.text or "").strip()
        if text and text.isdigit():
            return {
                "ok": True, "found": True,
                "display_name": username,
                "extra": {"twitch_id": int(text)},
            }
        if "User not found" in text:
            return {"ok": True, "found": False, "status": 404}

    # 2) Fallback: Twitch GQL (only catches users that have streamed)
    r = await safe_get(
        client,
        f"https://gql.twitch.tv/gql",
        timeout=6.0,
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}

    # Make the actual GQL request manually (it's a POST with a body)
    try:
        gql_r = await client.post(
            "https://gql.twitch.tv/gql",
            json=[{
                "operationName": "UseLive",
                "variables": {"channelLogin": username},
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "639d5f11bfb8bf3053b424d9ef650d04c4ebb7d94711d644afb08fe9a0fad5d9",
                    }
                },
            }],
            headers={"Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko", "Content-Type": "application/json"},
            timeout=6.0,
        )
    except Exception:
        return {"ok": True, "found": False}
    if gql_r.status_code != 200:
        return {"ok": True, "found": False}
    try:
        j = gql_r.json()
    except Exception:
        return {"ok": True, "found": False}
    if isinstance(j, list) and j and j[0].get("data", {}).get("user"):
        return {"ok": True, "found": True, "display_name": username}
    return {"ok": True, "found": False}


async def check_telegram(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://t.me/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    title = title_of(text) or ""
    meta = parse_meta(text)
    if "You can contact" in text and "Telegram" in text:
        return {
            "ok": True, "found": True,
            "display_name": pick_display_name(meta, title, username),
            "avatar_url": pick_avatar(meta),
        }
    # If the page shows the error "If you have <strong>username</strong>, you can contact …"
    if "tgme_page_icon" not in text and "tgme_page_title" not in text:
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(meta, title, username),
        "avatar_url": pick_avatar(meta),
    }


async def check_pinterest(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://www.pinterest.com/{username}/")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    if len(text) < 50_000:
        return {"ok": True, "found": False}
    meta = parse_meta(text)
    if "pinterest.com" not in (meta.get("og:url") or ""):
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(meta, title_of(text), username),
        "bio": meta.get("og:description"),
        "avatar_url": pick_avatar(meta),
    }


async def check_snapchat(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Snapchat: real-profile pages are ~110KB, missing-user redirects are ~7KB."""
    r = await safe_get(client, f"https://www.snapchat.com/add/{username}")
    if r is None or r.status_code >= 400:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    if len(text) < 30_000:
        return {"ok": True, "found": False}
    title = title_of(text) or ""
    meta = parse_meta(text)
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(meta, title, username),
        "bio": meta.get("og:description"),
        "avatar_url": pick_avatar(meta),
    }


async def check_spotify(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://open.spotify.com/user/{username}")
    if r is None:
        return {"ok": False, "found": False}
    if r.status_code == 200:
        text = r.text or ""
        title = title_of(text) or ""
        # Spotify renders the same shell for all users; real users show
        # the user name in <title>
        if username.lower() in title.lower() or "Spotify" not in title:
            meta = parse_meta(text)
            return {
                "ok": True, "found": True,
                "display_name": pick_display_name(meta, title, username),
                "avatar_url": pick_avatar(meta),
            }
    return {"ok": True, "found": False, "status": r.status_code}


async def check_devto(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(
        client, f"https://dev.to/api/users/by_username?url={username}",
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    if not isinstance(j, dict) or j.get("error"):
        return {"ok": True, "found": False}
    if j.get("username", "").lower() != username.lower():
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": j.get("name"),
        "bio": j.get("summary"),
        "avatar_url": j.get("profile_image"),
    }


async def check_medium(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Medium uses Cloudflare bot protection. We try a direct fetch and
    accept either 'Just a moment...' (challenge) or a real profile page.
    If we get a real HTML with og:title containing the username, treat
    as found."""
    r = await safe_get(client, f"https://medium.com/@{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    if "Just a moment" in text:
        return {"ok": True, "found": None, "extra": {"reason": "cloudflare_challenge"}}
    meta = parse_meta(text)
    title = title_of(text) or ""
    if meta.get("og:title") and username.lower() in title.lower():
        return {
            "ok": True, "found": True,
            "display_name": pick_display_name(meta, title, username),
            "avatar_url": pick_avatar(meta),
        }
    return {"ok": True, "found": False}


async def check_behance(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://www.behance.net/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    title = title_of(text) or ""
    if "Oops" in title or "can't find" in title.lower():
        return {"ok": True, "found": False}
    meta = parse_meta(text)
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(meta, title, username),
        "avatar_url": pick_avatar(meta),
    }


async def check_dribbble(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://dribbble.com/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    title = title_of(text) or ""
    if "Page Not Found" in title or "Not Found" in title:
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(parse_meta(text), title, username),
        "avatar_url": pick_avatar(parse_meta(text)),
    }


async def check_vimeo(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://vimeo.com/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    title = title_of(r.text or "") or ""
    if title.lower().startswith("vimeuhoh"):
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(parse_meta(r.text or ""), title, username),
        "avatar_url": pick_avatar(parse_meta(r.text or "")),
    }


async def check_hackernews(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(
        client, f"https://hacker-news.firebaseio.com/v0/user/{username}.json",
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    if not isinstance(j, dict) or not j:
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": j.get("id", "").lower() == username.lower(),
        "display_name": j.get("about"),
    }


async def check_stackoverflow(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(
        client,
        f"https://api.stackexchange.com/2.3/users?site=stackoverflow&inname={username}",
    )
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    try:
        j = r.json()
    except Exception:
        return {"ok": True, "found": False}
    items = (j or {}).get("items") or []
    if not items:
        return {"ok": True, "found": False}
    first = items[0]
    return {
        "ok": True, "found": True,
        "display_name": first.get("display_name"),
        "avatar_url": first.get("profile_image"),
        "extra": {"reputation": first.get("reputation")},
    }


async def check_mastodon(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    """Probe the public /api/v1/accounts/lookup endpoint on a few
    federated Mastodon instances. Real users return a full account;
    missing users return 404."""
    instances = (
        "https://mastodon.social",
        "https://mastodon.online",
        "https://mas.to",
        "https://infosec.exchange",
        "https://scholar.social",
        "https://mstdn.social",
        "https://hachyderm.io",
    )
    for base in instances:
        r = await safe_get(
            client, f"{base}/api/v1/accounts/lookup",
            headers={"Accept": "application/json"},
        )
        if r is None or r.status_code != 200:
            continue
        try:
            j = r.json()
        except Exception:
            continue
        if isinstance(j, dict) and j.get("id"):
            return {
                "ok": True, "found": True,
                "display_name": j.get("display_name"),
                "profile_url": j.get("url"),
                "avatar_url": j.get("avatar"),
                "extra": {
                    "instance": base,
                    "followers_count": j.get("followers_count"),
                    "verified": j.get("verified"),
                },
            }
    return {"ok": True, "found": False}


async def check_aboutme(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://about.me/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    if "Page Not Found" in text or "Not Found" in text:
        return {"ok": True, "found": False}
    title = title_of(text) or ""
    meta = parse_meta(text)
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(meta, title, username),
        "avatar_url": pick_avatar(meta),
    }


async def check_soundcloud(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    r = await safe_get(client, f"https://soundcloud.com/{username}")
    if r is None or r.status_code != 200:
        return {"ok": r is not None, "found": False}
    text = r.text or ""
    title = title_of(text) or ""
    if "Page Not Found" in title or "Not Found" in title:
        return {"ok": True, "found": False}
    return {
        "ok": True, "found": True,
        "display_name": pick_display_name(parse_meta(text), title, username),
        "avatar_url": pick_avatar(parse_meta(text)),
    }
