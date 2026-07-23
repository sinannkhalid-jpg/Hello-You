# OSINT Nexus

> A production-quality **educational** OSINT platform for authorized investigations, cybersecurity education, and analysis of **publicly available** information.

> **Ethics & scope.** OSINT Nexus is built strictly for:
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

## Repo layout

```
osint-nexus/
├── api/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/         # Routers
│   │   ├── core/           # Config, security, deps
│   │   ├── db/             # SQLAlchemy session & base
│   │   ├── models/         # ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   ├── osint/          # OSINT providers (real public APIs)
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── web/                    # Next.js frontend (Step 2+)
├── migrations/             # SQL migration files
├── docs/                   # API + deployment docs
└── README.md
```

---

## Quick start

```bash
# Backend
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in values
uvicorn app.main:app --reload --port 8000
# OpenAPI docs at http://localhost:8000/docs
```

See `docs/DEPLOYMENT.md` for Vercel + Render + Supabase deployment, and `docs/API.md` for the full API reference.

---

## Modules (sidebar)

Dashboard · Username · Email · Phone · Domain · IP · DNS · WHOIS · SSL · Certificate Transparency · Subdomain Discovery · Technology Detection · Relationship Graph · AI Report · Saved Investigations · Settings.

---

## License

MIT. Use responsibly.
