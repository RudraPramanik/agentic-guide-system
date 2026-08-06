# Wandr — Frontend stack & API integration guide

> **Canonical FE contract** for the separate Next.js app (sibling repo, not a monorepo).  
> Draft brainstorming lives in `docs/fe_suggestins.md` — **this file is the locked subset**.  
> Live API routes: `docs/context.md` → Live endpoints. Update this guide when routes change.

**Non-goals of this document:** scaffolding the Next.js app inside this API repo; changing FastAPI code; frontend hosting/VPS SOP.

---

## 1. Product & repo relationship

| Repo | Role |
|------|------|
| This repo (`guideagent`) | FastAPI backend + this guide |
| Sibling FE repo (e.g. `wandr-web`) | Next.js App Router UI |

When the API is reachable at a stable host, the FE switches only:

```bash
NEXT_PUBLIC_API_URL=https://api.example.com   # prod
# NEXT_PUBLIC_API_URL=http://localhost:8000   # local
```

Same build, same screens, same clients — no DB/Redis/LLM env in the frontend.

```
Dev:  Next :3000  ──credentials──▶  uvicorn :8000  ◀── docker compose (PostGIS + Qdrant)
Prod: app.<domain> ──credentials──▶  api.<domain>   ◀── hosted DB / Qdrant / Redis / LLM
```

---

## 2. Locked MVP stack

| Layer | Choice | Role |
|-------|--------|------|
| Framework | Next.js App Router (stable 15/16 line) | RSC + client islands |
| Language | TypeScript (strict) | Required |
| Styling | Tailwind CSS v4 | Utility CSS |
| Components | shadcn/ui | Copy-in primitives |
| Icons | Lucide | Lightweight |
| Motion | Motion | Generate/progress UI motion |
| Forms | React Hook Form + Zod | Client validation |
| Server state | TanStack Query v5 | Destinations, trips, mutations |
| UI state | Zustand (thin) | Wizard / map selection only — not Redux |
| Theme | next-themes | Light/dark (optional) |
| Toasts | Sonner | Errors, claim/edit feedback |
| Dates | date-fns | Lightweight formatting |
| Maps | MapLibre GL + OSM-compatible tiles | Trip GeoJSON + polylines |
| Markdown (optional) | react-markdown + remark-gfm | Day narrative prose only |
| Tests | Vitest + RTL; Playwright smoke | Unit + e2e smoke |
| Lint | ESLint + Prettier | FE repo standards |

**Quality (light):** Husky/lint-staged optional. Sentry optional. PostHog deferred.

---

## 3. Deferred / rejected (from generic AI SaaS draft)

| Item | Status | Why |
|------|--------|-----|
| Vercel AI SDK as primary planner client | **Deferred** | Backend SSE is phase/tool progress, not chat tokens |
| Better Auth / NextAuth owning sessions | **Rejected (MVP)** | FastAPI already sets httpOnly cookies |
| Chat / notebook / workspace product shell | **Rejected (MVP)** | Wandr shell is search → generate → trip + map |
| TanStack Table, Recharts/Tremor | **Deferred** | No admin dashboard in MVP |
| WebSockets | **Deferred** | Unidirectional planner SSE is enough |
| File uploads (dropzone, R2/S3) | **Deferred** | No upload APIs |
| Mermaid / LaTeX / heavy code blocks | **Deferred** | Not needed for itinerary narrative |
| Redux | **Rejected** | Overkill vs Query + thin Zustand |
| Google Maps as primary SDK | **Deferred** | MapLibre + GeoJSON matches backend |
| Next.js BFF / rewrites | **Deferred** | Direct browser → API + CORS for MVP |

---

## 4. Environment variables

### Frontend only

| Variable | Example | Notes |
|----------|---------|--------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API origin, no trailing slash |
| (optional) map tile URL / key | OSM public or MapTiler later | Not required for first local map |

**Never put in the frontend:** `DATABASE_URL`, `REDIS_URL`, `QDRANT_*`, `LLM_*`, `GEMINI_API_KEY`, `SECRET_KEY`, OAuth client secrets.

### Backend (must match FE host — configured on API, not in Next)

| Variable | Purpose |
|----------|---------|
| `CORS_ALLOWED_ORIGINS` | Must include FE origin (e.g. `["http://localhost:3000"]` or `["https://app.…"]`) — never `*` with cookies |
| `GOOGLE_REDIRECT_URI` | API callback URL |
| `GOOGLE_CLIENT_ID` / `SECRET` | OAuth |
| Data plane | `DATABASE_URL`, `QDRANT_*`, `REDIS_URL`, `LLM_*`, embeddings |

Production cookie model (Option A): put `app.` and `api.` under the **same registrable domain** so `SameSite=Lax` works.

---

## 5. Auth, cookies, CORS

FastAPI owns auth. The FE is a **cookie client**.

| Cookie | httpOnly | Purpose |
|--------|----------|---------|
| `wandr_session` | yes | Guest trip ownership |
| `wandr_token` | yes | JWT after Google login |

**Rules:**

1. Every cookie-scoped call MUST use `credentials: "include"`.
2. Do **not** store access tokens in `localStorage` or readable JS cookies.
3. Prefer `GET {API_URL}/api/v1/auth/me` to learn guest vs user.
4. Login: navigate/redirect to `GET {API_URL}/api/v1/auth/google`.
5. Logout: `POST {API_URL}/api/v1/auth/logout` with credentials.
6. After login, keep the same browser session so `wandr_session` still matches for `POST /trips/{id}/claim`.

Local: `localhost:3000` ↔ `localhost:8000` is fine with CORS + Lax.  
Prod: same registrable domain (`app.` + `api.`).

---

## 6. Response envelopes

Most JSON endpoints use:

```ts
// success
{ success: true, data: T, message?: string }

// error (global handler)
{ success: false, code: string, message: string, details?: object }
```

Paginated list endpoints use `PaginatedResponse` (see backend `src/core/pagination.py`).

**Exception:** `POST /api/v1/planner/generate` streams **SSE frames**, not `ApiResponse`.

Build one shared `lib/api/client.ts` that:

- prefixes `NEXT_PUBLIC_API_URL`
- sets `credentials: "include"`
- parses success/error envelopes
- throws typed errors on `success: false` or non-OK HTTP

---

## 7. Planner SSE contract

Endpoint: `POST /api/v1/planner/generate`  
Body (see `PlanRequest`): `destination_id`, `raw_input`, optional days/base/accommodation fields.

**Do not use** the browser `EventSource` API — it is GET-only.

Use `fetch` + `ReadableStream` and parse frames:

```
event: <name>
data: <json>

```

| Kind | Events |
|------|--------|
| Progress (examples) | `preferences_done`, `phase_changed`, `tool_started` / `tool_done` / `tool_batch_done`, … |
| Terminal | `itinerary_done` (may include `trip_id`), `error`, `clarification_needed` |

On success path, persist runs server-side; terminal `itinerary_done` is enriched with `trip_id` when save succeeds. Floor check: low destination `place_count` → HTTP **409** `destination_not_ready` (before stream).

Proxy note (prod): reverse proxy must not buffer this path (see `docs/context.md` / production blueprint).

Optional later: Vercel AI SDK only if you add a true chat surface — **not** as the MVP planner client.

---

## 8. Domain API modules ↔ live endpoints

Organize `lib/api/` by Wandr domains (not Chat/Notebook/Workspace):

### `auth`

| Method | Path |
|--------|------|
| GET | `/api/v1/auth/google` |
| GET | `/api/v1/auth/callback` (Google → API; see §11 gap) |
| GET | `/api/v1/auth/me` |
| POST | `/api/v1/auth/logout` |

### `destinations`

| Method | Path |
|--------|------|
| GET | `/api/v1/destinations/search?q=` |
| GET | `/api/v1/destinations/{id}/readiness` |

### `places`

| Method | Path |
|--------|------|
| GET | `/api/v1/places?destination_id=` |
| GET | `/api/v1/places/{id}` |

### `planner`

| Method | Path |
|--------|------|
| POST | `/api/v1/planner/generate` (SSE) |

### `trips`

| Method | Path |
|--------|------|
| GET | `/api/v1/trips` |
| GET | `/api/v1/trips/{id}` |
| GET | `/api/v1/trips/{id}/geojson` |
| DELETE | `/api/v1/trips/{id}` |
| POST | `/api/v1/trips/{id}/claim` |
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` |
| POST | `/api/v1/trips/{id}/days/{day}/stops` |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` |

Also available: `GET /api/v1/health` (ops/smoke).

Wrap each module with TanStack Query hooks (`useQuery` / `useMutation` + invalidation on edit/claim).

**Evaluation HTTP** is still stub on the backend — do not invent FE screens that call it.

---

## 9. MVP screen flow

```
[Search destination]
        ↓
[Readiness] place_count / search_available
        ↓
[Compose] raw_input (+ optional days / base)
        ↓
[Generating…] SSE phase/tool progress
        ↓
[Trip] day list + MapLibre (GeoJSON / polylines)
        ↓
[Edit] reorder / add / remove / reoptimize   (auth)
        ↓
[Claim] after Google login                   (auth + wandr_session)
```

This is **not** a multi-turn chat notebook as the primary shell. Progress UI should surface planner phases/tools; the durable artifact is the **trip**.

---

## 10. Local verification loop

In the **API** repo:

```bash
docker compose up -d          # PostGIS :5433, Qdrant :6335 only
# configure .env (DATABASE_URL, LLM_*, CORS includes http://localhost:3000)
uvicorn src.main:app --reload --port 8000
# seed + enrich + index at least one destination (see docs/context.md scripts)
```

In the **FE** repo:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev   # http://localhost:3000
```

Happy path: search → readiness OK → generate → open trip → map from `/geojson`.

---

## 11. Known gap — OAuth return to app

Today Google redirects to the **API** (`GOOGLE_REDIRECT_URI=…/api/v1/auth/callback`). On success the API returns **JSON + Set-Cookie**, not a redirect to the Next.js origin. Failures redirect to `/auth/error` on the API host.

**MVP:** ship guest generate → trip → map without depending on polished login return.  
**Follow-up (backend):** add something like `FRONTEND_URL` and redirect after setting `wandr_token` (e.g. to `{FRONTEND_URL}/auth/done` or deep-link to trip). Until then, document login UX as incomplete.

---

## 12. Suggested FE repo layout (feature-first)

```
app/                    # App Router routes
components/
  ui/                   # shadcn
  map/
  generate/             # SSE progress
features/
  auth/
  destinations/
  planner/
  trips/
hooks/
lib/
  api/                  # auth, destinations, places, planner, trips + client.ts
  sse/                  # planner stream parser
  utils/
store/                  # zustand UI stores
types/
providers/              # QueryClient, theme, toaster
```

Prefer feature folders over dumping everything under `components/` as the app grows.

---

## 13. Checklist before pointing FE at production API

- [ ] API HTTPS up; health OK  
- [ ] Destination seeded/indexed on **prod** data plane  
- [ ] `CORS_ALLOWED_ORIGINS` includes prod FE origin  
- [ ] `app.` + `api.` same registrable domain (Option A)  
- [ ] SSE path not buffered by proxy  
- [ ] FE `NEXT_PUBLIC_API_URL` set to API origin  
- [ ] OAuth redirect URIs updated (and ideally `FRONTEND_URL` bounce landed)

---

*Source decisions: OpenSpec change `frontend-stack-guide`. Input draft: `docs/fe_suggestins.md`.*
