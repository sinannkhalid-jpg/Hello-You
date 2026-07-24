"""
Gravatar provider.

Uses the public, unauthenticated `https://www.gravatar.com/{hash}.json`
endpoint. The Gravatar hash is MD5 of the lowercased/trimmed email.

Returns the user's profile if one exists.
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.services.providers.base import BaseProvider
from app.services.providers.http import get_json


def _hash_email(email: str) -> str:
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


class GravatarProvider(BaseProvider):
    name = "gravatar"
    kind = "email"
    enabled = True
    requires_key = False
    rate_limit_per_minute = 60
    cache_ttl = 60 * 60 * 24
    timeout_seconds = 8.0
    health_url = "https://www.gravatar.com/"

    async def lookup(self, target: str, **kwargs: Any) -> dict[str, Any]:
        if "@" not in target:
            return {
                "found": False,
                "reason": "Gravatar lookup requires an email",
            }

        h = _hash_email(target)
        data = await get_json(f"https://www.gravatar.com/{h}.json")

        # Gravatar returns 404 for non-existent profiles. The http helper
        # already returns None in that case.
        if not data or not isinstance(data, dict):
            return {
                "found": False,
                "hash": h,
                "avatar_url": f"https://www.gravatar.com/avatar/{h}?d=404",
            }

        entries = data.get("entry") or []
        if not entries:
            return {
                "found": False,
                "hash": h,
                "avatar_url": f"https://www.gravatar.com/avatar/{h}?d=404",
            }

        first = entries[0] if isinstance(entries[0], dict) else {}
        profile = first.get("profile") or {}
        photos = first.get("photos") or []
        thumb = None
        if photos and isinstance(photos[0], dict):
            thumb = photos[0].get("value")

        display_name = (
            profile.get("displayName")
            or profile.get("preferredUsername")
            or (first.get("displayName") if isinstance(first, dict) else None)
        )

        # Map Gravatar's link list to common accounts
        accounts: list[dict[str, str]] = []
        for link in first.get("accounts", []) or []:
            if not isinstance(link, dict):
                continue
            accounts.append({
                "platform": link.get("shortname") or link.get("domain") or "unknown",
                "url": link.get("url") or "",
                "username": link.get("username") or "",
                "verified": bool(link.get("verified")),
            })

        return {
            "found": True,
            "hash": h,
            "avatar_url": thumb or f"https://www.gravatar.com/avatar/{h}?d=404",
            "display_name": display_name,
            "profile_url": profile.get("profileUrl") or f"https://en.gravatar.com/{first.get('preferredUsername', '')}",
            "about_me": profile.get("aboutMe"),
            "current_location": profile.get("currentLocation"),
            "accounts": accounts,
        }


PROVIDER_CLASS = GravatarProvider
