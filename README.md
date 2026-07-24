# Hello You

> A production-quality **educational** OSINT platform for authorized investigations, cybersecurity education, and analysis of **publicly available** information.

> **Ethics & scope.** Hello You is built strictly for:
> - Authorized security testing on systems you own or have written permission to test.
> - Cybersecurity education and research.
> - Analysis of data that is already publicly available.
>
> It must **not** be used for unauthorized access, hacking, credential theft, malware distribution, doxxing, harassment, or any privacy violation. Several modules (port scanning, breach lookups, etc.) are gated behind confirmation of authorization.

---

## Stack

| Layer        | Technology                                            |
|--------------|--------------------------------------------------------|
| Frontend     | Next.js 14 (App Router) · React · TypeScript · Tailwind · shadcn/ui · React Query · React Flow · Framer Motion · Recharts · Leaflet |
| Backend      | FastAPI · Python 3.11 · Pydantic v2 · SQLAlchemy 2 (async) · Uvicorn |
| Database     | PostgreSQL (Supabase)                                  |
| Auth         | Supabase Auth (email + Google) — with a local JWT stub fallback |
| Hosting      | Vercel (web) · Render (api) · Supabase (db)            |

Everything runs on free tiers.

---

## OSINT providers (all key-gated, all skippable)

Each provider auto-loads its API key from environment. If a key is missing
the provider is silently disabled — no errors, no partial lookups.

| Provider        | Kind    | Key env var             | Required key? |
|-----------------|---------|-------------------------|---------------|
| Have I Been Pwned | email  | `HIBP_API_KEY`          | Yes (paid)    |
| VirusTotal      | domain / ip | `VIRUSTOTAL_API_KEY` | Yes (free tier) |
| AbuseIPDB       | ip      | `ABUSEIPDB_API_KEY`     | Yes (free tier) |
| Shodan          | ip      | `SHODAN_API_KEY`        | Yes (free tier) |
| SecurityTrails  | domain  | `SECURITYTRAILS_API_KEY`| Yes (paid)    |
| IPAPI           | ip      | `IPAPI_KEY`             | No (free tier) |
| Gravatar        | email   | (none)                  | No            |
| crt.sh          | domain  | (none)                  | No            |
| DNS             | domain  | (none)                  | No            |
| WHOIS / RDAP    | domain  | (none)                  | No            |
| LeakCheck       | email   | `LEAKCHECK_API_KEY`     | No (key raises quota) |
| Censys          | ip      | `CENSYS_API_ID` + `CENSYS_API_SECRET` | Yes (paid) |
| IntelX          | domain  | (none)                  | No            |

### Adding a new provider

Drop a file at `api/app/services/providers/<name>.py` that subclasses
`BaseProvider`, then add it to the registry — or simply set
`OSINT_EXTRA_PROVIDERS=shodan` to auto-load from env. See
[docs/API.md](docs/API.md) for the full provider reference.

---

## Repo layout

```
hello-you/
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # Routers
│   │   ├── core/           # Config, security, deps
│   │   ├── db/             # SQLAlchemy session & base
│   │   ├── models/         # ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic + providers
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── web/                    # Next.js 14 frontend
│   ├── src/
│   │   ├── app/            # (auth) + (app) routes
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── styles/
│   │   └── types/
│   └── package.json
├── migrations/             # SQL migration files
├── docs/                   # API + deployment docs
└── README.md
```

---

## Quick start

### Backend
```bash
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in values
uvicorn app.main:app --reload --port 8000
# OpenAPI docs at http://localhost:8000/docs
```

### Frontend
```bash
cd web
npm install
cp .env.example .env.local
npm run dev
# open http://localhost:3000
```

See `docs/DEPLOYMENT.md` for Vercel + Render + Supabase deployment, and
`docs/API.md` for the full API reference.

---

## License

MIT. Use responsibly.
