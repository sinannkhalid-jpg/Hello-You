# Hello You — Web (Next.js 14)

The frontend. Talks to the FastAPI backend in `/api`.

## Stack

Next.js 14 (App Router) · React 18 · TypeScript · Tailwind CSS · shadcn/ui ·
@tanstack/react-query · React Flow · Framer Motion · Recharts · Leaflet.

## Quick start

```bash
cd web
npm install
cp .env.example .env.local       # set NEXT_PUBLIC_API_URL
npm run dev
# open http://localhost:3000
```

## Build

```bash
npm run build
npm start
```

## Project layout

```
src/
├── app/
│   ├── (auth)/           # /login /register /forgot
│   ├── (app)/            # authenticated app routes
│   │   ├── dashboard/    # stats + charts
│   │   ├── username/     # OSINT module pages
│   │   ├── email/
│   │   ├── phone/
│   │   ├── domain/
│   │   ├── ip/           # includes Leaflet map
│   │   ├── dns/
│   │   ├── whois/
│   │   ├── ssl/
│   │   ├── ct/
│   │   ├── subdomains/
│   │   ├── tech/
│   │   ├── graph/        # React Flow
│   │   ├── report/       # AI-style report
│   │   ├── investigations/   # list + detail
│   │   └── settings/
│   ├── layout.tsx
│   ├── page.tsx          # landing
│   └── providers.tsx     # QueryClient + Auth + Cyber BG + Toaster
├── components/
│   ├── ui/               # shadcn/ui primitives
│   ├── layout/           # Sidebar, Topbar, AppShell
│   ├── charts/           # Recharts wrappers + RiskGauge
│   ├── effects/          # CyberBackground, Radar, Typewriter, NetworkScan
│   ├── modules/          # ModuleShell, KeyValueGrid, GraphCanvas, IpMap
│   └── common/           # Loading, EmptyState, StatCard, ThreatChip, etc.
├── hooks/                # useTargetParam
├── lib/                  # api.ts, auth.tsx, queryClient.ts, utils.ts
├── styles/globals.css    # Tailwind + glassmorphism + cyber grid
└── types/osint.ts
```

## Environment

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL (default `http://localhost:8000`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Optional Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Optional Supabase anon key |
| `NEXT_PUBLIC_USE_SUPABASE` | `true` to enable Supabase login |

## Notes

- The app is fully responsive down to iPhone 12 (390×844). The sidebar collapses
  to a hamburger drawer below `md`.
- Dark cyberpunk theme is the default; light mode is not shipped.
- All module pages accept a `?target=…` query param so URLs are shareable.
- Animation effects: animated sidebar pill (Framer Motion `layoutId`), scan-line
  overlays, typewriters, drifting cyber grid, particles.
