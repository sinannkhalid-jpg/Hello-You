"""Username enumeration across public profile URLs (no auth required).

We send a HEAD/GET request to the well-known public profile URL of each
platform. If the page returns 2xx, the username is taken. We do not
bypass rate limits; we rely on each platform's public unauthenticated
HTML pages only. We never request data behind a login.

This is implemented as opt-in per platform; clients can disable any
network call by removing entries from the list.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.logging import get_logger

log = get_logger(__name__)

# Public profile URL templates. Only unauthenticated, public pages.
PLATFORMS: dict[str, str] = {
    "GitHub":     "https://github.com/{u}",
    "GitLab":     "https://gitlab.com/{u}",
    "Twitter/X":  "https://x.com/{u}",
    "Reddit":     "https://www.reddit.com/user/{u}/about.json",
    "Instagram":  "https://www.instagram.com/{u}/",
    "TikTok":     "https://www.tiktok.com/@{u}",
    "YouTube":    "https://www.youtube.com/@{u}",
    "Medium":     "https://medium.com/@{u}",
    "Dev.to":     "https://dev.to/{u}",
    "StackOverflow": "https://stackoverflow.com/users/{u}",
    "HackerNews": "https://news.ycombinator.com/user?id={u}",
    "Pinterest":  "https://www.pinterest.com/{u}/",
    "Twitch":     "https://www.twitch.tv/{u}",
    "Steam":      "https://steamcommunity.com/id/{u}",
    "Spotify":    "https://open.spotify.com/user/{u}",
    "SoundCloud": "https://soundcloud.com/{u}",
    "Behance":    "https://www.behance.net/{u}",
    "Dribbble":   "https://dribbble.com/{u}",
    "Vimeo":      "https://vimeo.com/{u}",
    "About.me":   "https://about.me/{u}",
}


async def _check_one(client: httpx.AsyncClient, name: str, url: str, username: str) -> dict[str, Any] | None:
    target = url.format(u=username)
    try:
        r = await client.get(target, follow_redirects=True, timeout=8.0)
    except httpx.HTTPError as e:
        log.debug("username check %s failed: %s", name, e)
        return None
    exists = r.status_code == 200 and len(r.text) > 200
    if not exists:
        return None

    profile: dict[str, Any] = {
        "platform": name,
        "url": target,
        "exists": True,
        "username": username,
        "confidence": 0.9,
    }
    # Extract a few common signals cheaply from the HTML.
    text = r.text
    if "<title>" in text:
        try:
            title = text.split("<title>", 1)[1].split("</title>", 1)[0].strip()
            profile["display_name"] = title[:120]
        except Exception:
            pass
    if "description" in text:
        try:
            after = text.split('name="description"', 1)[1]
            content = after.split('content="', 1)[1].split('"', 1)[0]
            if content and len(content) < 400:
                profile["bio"] = content
        except Exception:
            pass
    return profile


async def enumerate_username(username: str, max_concurrency: int = 8) -> list[dict[str, Any]]:
    if not username or len(username) > 64:
        return []
    sem = asyncio.Semaphore(max_concurrency)
    results: list[dict[str, Any] | None] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": "OSINT-Nexus/1.0 (+educational)"},
        follow_redirects=True,
        http2=False,
    ) as client:
        async def _task(name: str, url: str) -> None:
            async with sem:
                results.append(await _check_one(client, name, url, username))

        await asyncio.gather(*[_task(n, u) for n, u in PLATFORMS.items()])

    return [r for r in results if r]
