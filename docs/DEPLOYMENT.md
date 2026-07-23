# Deployment guide

This monorepo deploys to three managed services (all free tiers):

- **Frontend** (Next.js) → Vercel
- **Backend**  (FastAPI) → Render
- **Database** (Postgres) → Supabase

---

## 1. Supabase (database)

1. Create a project at <https://supabase.com>.
2. In **SQL Editor**, paste the contents of `migrations/0001_init.sql` and run.
3. From **Project Settings → Database**, copy the connection strings:
   - `DATABASE_URL` (Transaction pooler, port 6543) → use as `DATABASE_URL`
   - `DIRECT_URL`  (Session pooler, port 5432)   → use as `DIRECT_URL`
4. Optional: enable **Auth** in Supabase if you want Supabase-managed login.
   Copy the project URL and `anon` key to your env.

## 2. Render (backend)

1. Create a new **Web Service** from your repo, root `api/`.
2. Runtime: **Python 3.11**. Build: `pip install -r requirements.txt`.
   Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
3. Add env vars from `api/.env.example`. At minimum:
   - `DATABASE_URL=postgresql+asyncpg://...`
   - `SECRET_KEY=<random 32+ chars>`
   - `CORS_ORIGINS=https://<your-vercel-domain>`
4. Deploy. Copy the public URL (e.g. `https://osint-nexus-api.onrender.com`).

### Alternative: Render + Docker

The included `api/Dockerfile` works on Render if you pick "Docker" as the
environment. The `Procfile` and `runtime.txt` cover the non-Docker path.

## 3. Vercel (frontend)

1. Import the repo into Vercel. Set the **Root Directory** to `web/`
   (we'll create this in Step 2 of the build).
2. Add env var `NEXT_PUBLIC_API_URL=https://osint-nexus-api.onrender.com`.
3. Deploy. Copy the domain.

## 4. Smoke test

1. Open the Vercel URL.
2. Register a user, log in, run a `/api/v1/dns/example.com` lookup.
3. Confirm an `investigations` row appears in Supabase.

---

## Self-hosting (Docker Compose, optional)

```yaml
version: "3.9"
services:
  api:
    build: ./api
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/postgres
      SECRET_KEY: change-me
      CORS_ORIGINS: http://localhost:3000
    ports: ["8000:8000"]
    depends_on: [db]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: ["db:/data"]

volumes:
  db:
```

Run with: `docker compose up --build`.

---

## Production checklist

- [ ] Strong `SECRET_KEY` (32+ random chars)
- [ ] `CORS_ORIGINS` set to your real domain only
- [ ] `APP_DEBUG=false`
- [ ] HTTPS-only cookies (handled by Render/Vercel at the proxy)
- [ ] DB password rotated
- [ ] Optional: enable Supabase Auth and set `USE_SUPABASE=true`
- [ ] Optional: set `HIBP_API_KEY`, `ABUSEIPDB_API_KEY` for richer intel
