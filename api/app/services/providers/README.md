# OSINT providers

Every provider in this package implements the `BaseProvider` interface and is
auto-discovered by the orchestrator. Each provider returns a canonical envelope:

```json
{
  "provider": "virustotal",
  "ok": true,
  "found": true,
  "error": null,
  "cached": false,
  "response_time_ms": 247,
  "confidence": 0.85,
  "data": { ...provider-specific... }
}
```

The fields `provider`, `ok`, `found`, `error`, `cached`, `response_time_ms`,
`confidence` are present on every result. The `data` field is provider-specific
but always contains a `found` boolean and a `score` (0..100) when applicable.

## Built-in providers

| Provider        | Kind    | Key env var(s)                       | Required key? |
|-----------------|---------|---------------------------------------|---------------|
| VirusTotal      | domain / ip | `VIRUSTOTAL_API_KEY`             | Yes (free tier) |
| AbuseIPDB       | ip      | `ABUSEIPDB_API_KEY`                   | Yes (free tier) |
| Shodan          | ip      | `SHODAN_API_KEY`                      | Yes (free tier) |
| IPAPI           | ip      | `IPAPI_KEY` (optional)                | No (free tier) |
| Censys          | ip      | `CENSYS_PAT` *(new Platform API v3, preferred)* or `CENSYS_API_ID` + `CENSYS_API_SECRET` *(legacy v1)* | Yes (paid)    |
| HIBP            | email   | `HIBP_API_KEY`                        | Yes (paid)    |
| LeakCheck       | email   | `LEAKCHECK_API_KEY` (optional)        | No (key raises quota) |
| Gravatar        | email   | (none)                                | No            |
| SecurityTrails  | domain  | `SECURITYTRAILS_API_KEY`              | Yes (paid)    |
| crt.sh          | domain  | (none)                                | No            |
| IntelX          | domain  | (none)                                | No            |
| DNS             | domain  | (none)                                | No            |
| WHOIS / RDAP    | domain  | (none)                                | No            |
| Username        | username | (none)                               | No            |

## Adding a new provider

Two ways, no code edits required for either:

### 1. Auto-discover via env

```bash
# .env
OSINT_EXTRA_PROVIDERS=mynewprovider
```

```python
# api/app/services/providers/mynewprovider.py
from app.services.providers.base import BaseProvider

class MyNewProvider(BaseProvider):
    name = "mynewprovider"
    kind = "ip"             # or "domain", "email", "username", "url"
    requires_key = True
    api_key_env = "MYNEWPROVIDER_API_KEY"  # auto-loaded

    async def lookup(self, target, **kwargs):
        # ... your implementation ...
        return {"found": True, "score": 0, "threat_level": "low"}

PROVIDER_CLASS = MyNewProvider
```

That's it. The orchestrator auto-loads it on startup. It will appear in
`/api/v1/intel/providers` and `/api/v1/intel/health` immediately.

### 2. Built-in registration

If you want it always available (no env gating), add it to
`app/services/providers/registry.py`:

```python
from app.services.providers.mynewprovider import MyNewProvider

ALL_PROVIDERS.append(MyNewProvider)
PROVIDER_REGISTRY["ip"].append(MyNewProvider)
```

## Per-result shape (username investigation)

The username provider returns one entry per platform discovered. Each entry
includes all the required fields:

```json
{
  "platform": "GitHub",
  "profile_url": "https://github.com/octocat",
  "username": "octocat",
  "display_name": "The Octocat",
  "bio": "...",
  "avatar_url": "https://avatars.githubusercontent.com/u/583231",
  "verified": true,
  "found": true,
  "confidence": 0.95,
  "response_time_ms": 247,
  "reliable": true,
  "strategies": [
    {"name": "api",  "weight": 1.0, "ok": true,  "found": true,  "duration_ms": 41},
    {"name": "http", "weight": 0.5, "ok": true,  "found": true,  "duration_ms": 206}
  ]
}
```

## Multi-strategy detection

Each platform in the username provider is probed by 1+ independent strategies:

- `api`     — public, unauthenticated API endpoint (GitHub, GitLab, Reddit,
              Steam XML, Keybase, Gravatar, StackExchange, Dev.to,
              HackerNews, Mastodon, Instagram web_profile_info, Threads,
              Bitbucket, YouTube HTML)
- `http`    — public profile URL inspected for size + title heuristics
              (Facebook, Instagram fallback, TikTok, X/Twitter, Snapchat,
              LinkedIn, Pinterest, Telegram, Spotify, Mastodon fallback,
              SoundCloud, Behance, Dribbble, Vimeo, About.me, HackerNews
              fallback)
- `oembed`  — platform oEmbed endpoint (TikTok, Twitch fallback)
- `graphql` — public unauthenticated GraphQL (Twitch GQL)

Confidence is the weighted agreement of all strategies × a per-platform
reliability factor. See `app/services/providers/username.py` for details.

## Supported platforms (29)

GitHub, GitLab, Bitbucket, StackOverflow, Dev.to, HackerNews, Keybase,
Reddit, YouTube, TikTok, Mastodon, Twitch, Steam, Spotify, Twitter/X,
Instagram, Facebook, Threads, LinkedIn, Pinterest, Snapchat, Telegram,
Behance, Dribbble, Vimeo, SoundCloud, Gravatar, Medium, About.me.
