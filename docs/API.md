# Hello You — API reference

Base URL: `http://localhost:8000`
OpenAPI / Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

All endpoints under `/api/v1`. All write endpoints (and any endpoint that
returns user-specific data) require `Authorization: Bearer <token>`.

## Auth

| Method | Path                       | Body / params             | Returns          |
|-------:|----------------------------|---------------------------|------------------|
| POST   | `/api/v1/auth/register`    | `{email,password,full_name?}` | `{access_token,refresh_token,...}` |
| POST   | `/api/v1/auth/login`       | `{email,password}`        | token pair       |
| POST   | `/api/v1/auth/refresh`     | `{refresh_token}`         | token pair       |
| POST   | `/api/v1/auth/forgot-password` | `{email}`             | `{message}`      |
| GET    | `/api/v1/auth/me`          | —                         | current user     |
| POST   | `/api/v1/auth/logout`      | —                         | `{message}`      |

## Investigations

| Method | Path                                              | Notes |
|-------:|---------------------------------------------------|-------|
| GET    | `/api/v1/dashboard`                               | aggregated stats + timeline + risk dist + country dist |
| GET    | `/api/v1/investigations?kind=&favorite=&search=`  | paginated history |
| GET    | `/api/v1/investigations/{id}`                     | full result JSON |
| POST   | `/api/v1/investigations/{id}/favorite`            | toggle favorite |
| DELETE | `/api/v1/investigations/{id}`                     | delete |

## OSINT modules

| Method | Path                                                 | Module |
|-------:|------------------------------------------------------|--------|
| GET    | `/api/v1/username/{username}`                        | Username enumeration across 20 public platforms |
| GET    | `/api/v1/email/{email}`                              | Email (MX/SPF/DKIM/DMARC + Gravatar + optional HIBP) |
| GET    | `/api/v1/phone/{number}`                             | Phone metadata (libphonenumber, no PII) |
| GET    | `/api/v1/domain/{domain}`                            | Full domain investigation |
| GET    | `/api/v1/dns/{domain}`                               | DNS-only |
| GET    | `/api/v1/whois/{domain}`                             | RDAP/WHOIS |
| GET    | `/api/v1/ssl/{domain}`                               | TLS certificate details |
| GET    | `/api/v1/ct/{domain}?limit=50`                       | Certificate Transparency (crt.sh) |
| GET    | `/api/v1/subdomains/{domain}`                        | Subdomain discovery via CT |
| GET    | `/api/v1/tech/{domain}`                              | Technology detection (header + HTML) |
| GET    | `/api/v1/ip/{ip}`                                    | IP geo / ISP / ASN / threat intel |
| POST   | `/api/v1/ip/{ip}/port-scan` body `{"authorized":true}` | **Authorized only.** Plain TCP connect to common ports. |

## Graph

| Method | Path                                            | Notes |
|-------:|-------------------------------------------------|-------|
| GET    | `/api/v1/graph/investigation/{id}`              | derive graph from a saved investigation |
| POST   | `/api/v1/graph/from-data`                       | derive graph from a free-form payload |

## Reports

| Method | Path                                                  | Notes |
|-------:|-------------------------------------------------------|-------|
| POST   | `/api/v1/reports/generate` body `{target,kind,context,investigation_id?}` | AI-style report JSON |
| GET    | `/api/v1/reports/export/{inv_id}?fmt=pdf\|csv\|json` | Download |

## Settings

| Method | Path                              | Notes |
|-------:|-----------------------------------|-------|
| GET    | `/api/v1/settings/preferences`    | user prefs |
| PUT    | `/api/v1/settings/preferences`    | update |
| GET    | `/api/v1/settings/export`         | dump account as JSON |
| DELETE | `/api/v1/settings/account`        | GDPR-style delete |
| GET    | `/api/v1/settings/info`           | public app + provider status |

## Error model

```json
{ "error": "http_error", "status": 401, "detail": "Invalid credentials" }
```

## Rate limiting

60 requests/minute per IP by default. Set `RATE_LIMIT_PER_MINUTE` in `.env`.

## Data sources

- DNS: 1.1.1.1, 8.8.8.8, 9.9.9.9 (dnspython)
- IP geo: ipapi.co → ip-api.com fallback
- RDAP: IANA bootstrap → registry endpoints
- TLS: real TLS handshake + `cryptography` X.509 parsing
- CT: crt.sh
- Phone: `libphonenumber` (offline)
- HIBP / AbuseIPDB: only if you set the corresponding API keys
