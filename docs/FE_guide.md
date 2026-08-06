# Wandr — Frontend stack & API integration guide

> **Canonical FE contract** for the separate Next.js app (sibling repo, not a monorepo).  
> Draft brainstorming lives in `docs/fe_suggestins.md` — **this file is the locked subset**.  
> Live API routes: `docs/context.md` → Live endpoints. Update this guide when routes or public DTOs change.

**Non-goals of this document:** scaffolding the Next.js app inside this API repo; changing FastAPI code; frontend hosting/VPS SOP.

### API contract — source of truth

| Priority | Source | Role |
|----------|--------|------|
| 1 | Live routers + `src/*/schemas.py` | Canonical |
| 2 | OpenAPI at `{API}/docs` | Machine-readable companion |
| 3 | `docs/context.md` → Live endpoints | Auth matrix checkpoint |
| 4 | **This file** | FE-oriented mirror (stack + navigation) |

If this guide disagrees with Python schemas or `/docs`, **schemas win**. Update the API-contract sections of this file in the same PR (or immediately after) when public routes/DTOs change.

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
| Maps | MapLibre GL JS + MapTiler (see below) | Trip overlay GeoJSON |
| Markdown (optional) | react-markdown + remark-gfm | Day narrative prose only |
| Tests | Vitest + RTL; Playwright smoke | Unit + e2e smoke |
| Lint | ESLint + Prettier | FE repo standards |

### Map stack (explicit)

| Layer | Recommendation |
|-------|----------------|
| Renderer | MapLibre GL JS |
| Tile Provider | MapTiler (free tier) |
| Fallback | OpenStreetMap public tiles (**development only**) |
| Data Format | GeoJSON from FastAPI (`GET /trips/{id}/geojson` — §15) |
| Future | Self-hosted tiles or another provider |

Do **not** use OSM public tiles as the production basemap. Google Maps JS stays deferred as primary SDK (§3).

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
| `NEXT_PUBLIC_MAP_STYLE_URL` | MapTiler style JSON URL (often includes `?key=…`) | **Recommended** basemap for real/staging/prod |
| (optional) OSM / local style URL | Public OSM-compatible style or raster tiles | **Development only** when MapTiler is unset |

Prefer one style URL over scattering keys. If you build the MapTiler URL in code, a `NEXT_PUBLIC_MAPTILER_KEY` is acceptable — still FE-only. Never put MapTiler (or any tile) credentials in backend `.env`.

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

Most single-resource JSON endpoints use `ApiResponse[T]`:

```ts
// success
{ success: true, data: T, message?: string }

// error (global handler)
{ success: false, code: string, message: string, details?: object }
```

**Envelope exceptions (branch the client):**

| Response | Shape |
|----------|--------|
| `GET /places`, `GET /trips` | Bare `PaginatedResponse[T]` — **not** wrapped in `ApiResponse` |
| `GET /destinations/search` | `ApiResponse<DestinationOut[]>` (array in `data`) |
| `GET /trips/{id}/geojson` | Raw GeoJSON `FeatureCollection` — **not** `ApiResponse` |
| `POST /planner/generate` | SSE frames — **not** `ApiResponse` |
| `DELETE /trips/{id}` | HTTP **204** empty body |

Pagination query defaults: `page=1`, `size=20` (`size` max 100). See §14 for `PaginatedResponse` fields.

Build one shared `lib/api/client.ts` that:

- prefixes `NEXT_PUBLIC_API_URL`
- sets `credentials: "include"`
- parses success/error envelopes
- has separate parsers for pagination / GeoJSON / SSE
- throws typed errors on `success: false` or non-OK HTTP

---

## 7. Planner SSE contract

Endpoint: `POST /api/v1/planner/generate`  
Auth: **Optional** (guest via `wandr_session`; sets/creates session cookie on response).  
Body: `PlanRequest` — see §14.

**Do not use** the browser `EventSource` API — it is GET-only.

Use `fetch` + `ReadableStream` and parse frames:

```
event: <name>
data: <json>

```

### Progress vs terminal

| Kind | Events |
|------|--------|
| Progress | `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `tool_batch_done`, `validation_done`, … |
| Terminal (buffer until end; exactly one yielded) | `itinerary_done`, `error`, `clarification_needed` |

**Pre-stream failure:** destination `place_count` below planner floor → HTTP **409** `{ success: false, code: "destination_not_ready", … }` — **no SSE**.

**Cache replay:** may emit `preferences_done` / `phase_changed` / `itinerary_done` **without** `tool_started` / `tool_done`. Treat missing tool events as normal.

**After success:** prefer navigating to the trip via `trip_id` on `itinerary_done`, then `GET /trips/{id}` (+ `/geojson`). Do not treat the full SSE itinerary blob as the long-term UI model.

### Representative `data` keys (illustrative)

| Event | Typical `data` |
|-------|----------------|
| `preferences_done` | `{ interests, budget, days, include_offbeat, include_trekking }` |
| `phase_changed` | `{ phase: string, from_cache?: boolean }` |
| `tool_done` | `{ name: string, ok: boolean, code?: string \| null, ms: number }` |
| `tool_batch_done` | `{}` (may accompany state internally; FE can show “batch done”) |
| `itinerary_done` | `{ itinerary?, days?, from_cache?, trip_id?, accommodation_label? }` — `trip_id` added after save |
| `error` | `{ code: "generation_timeout" \| "graph_recursion_limit" \| string }` |
| `clarification_needed` | question / clarification payload (terminal; no trip save) |

Ignore unknown event names (log in dev). Spec catalog may include `tool_started` / `validation_done` even when a given run omits them.

Proxy note (prod): reverse proxy must not buffer this path (see `docs/context.md` / production blueprint).

Optional later: Vercel AI SDK only if you add a true chat surface — **not** as the MVP planner client.

---

## 8. Domain API modules ↔ live endpoints (auth matrix)

Organize `lib/api/` by Wandr domains (not Chat/Notebook/Workspace).  
Auth vocabulary: **None** | **Optional** | **Required** (+ ownership notes).

### Ops

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/health` | None | Smoke / ops |

### `auth`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/auth/google` | None | Start OAuth (redirect or not-configured message) |
| GET | `/api/v1/auth/callback` | None | Google → API only; see §11 gap |
| GET | `/api/v1/auth/me` | Optional | Guest or cookie/Bearer → `AuthMeResponse` |
| POST | `/api/v1/auth/logout` | None | Clears cookies; use `credentials: "include"` |

### `destinations`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/destinations/search?q=` | None | `q` min length 2; rate limit **20/min/IP**; `ApiResponse<DestinationOut[]>` |
| GET | `/api/v1/destinations/{id}/readiness` | None | `DestinationReadinessOut` — use `tier` / score / pcts (not a `search_available` field) |

### `places`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/places?destination_id=` | None | Bare `PaginatedResponse<PlaceOut>`; unknown destination → 404 |
| GET | `/api/v1/places/{id}` | None | `ApiResponse<PlaceOut>` |

### `planner`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api/v1/planner/generate` | Optional | SSE; floor 409 `destination_not_ready`; sets `wandr_session`; planner rate limit **10/min** |

### `trips`

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/api/v1/trips` | Required | Bare `PaginatedResponse<TripOut>` for authenticated user |
| GET | `/api/v1/trips/{id}` | Optional + ownership | Guest session **or** owner |
| GET | `/api/v1/trips/{id}/geojson` | None (public) | Raw `FeatureCollection` — see §15 |
| DELETE | `/api/v1/trips/{id}` | Required + ownership | **No anonymous delete**; HTTP 204 |
| POST | `/api/v1/trips/{id}/claim` | Required | Session must match; unclaimed only |
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | Required + owner | Body `ReorderStopsIn`; trip-edit rate limit |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | Required + owner | Trip-edit rate limit |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | Required + owner | Body `AddStopIn`; trip-edit rate limit |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | Required + owner | Trip-edit rate limit |

Wrap each module with TanStack Query hooks (`useQuery` / `useMutation` + invalidation on edit/claim).

**Evaluation HTTP** is still stub on the backend — do **not** invent FE screens or `lib/api/evaluation` modules that call it.

---

## 9. MVP screen flow

```
[Search destination]
        ↓
[Readiness] tier / score / place_count / enriched_pct / indexed_pct / message
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

Gate generate on readiness **tier** / message (and handle 409 `destination_not_ready`). There is **no** `search_available` boolean on the readiness JSON — Qdrant availability is folded into scoring / `indexed_pct` server-side.

This is **not** a multi-turn chat notebook as the primary shell. Progress UI should surface planner phases/tools; the durable artifact is the **trip**.

---

## 10. Local verification loop

In the **API** repo:

```bash
docker compose up -d          # PostGIS :5433, Qdrant :6335 only
# configure .env (DATABASE_URL, LLM_*, CORS includes http://localhost:3000)
uvicorn src.main:app --reload --port 8000
# seed + enrich + index at least one destination (see docs/context.md scripts)
# OpenAPI: http://localhost:8000/docs
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

## 14. DTO sketches (TypeScript mirrors)

> **Illustrative mirrors** of `src/*/schemas.py` + `src/core/responses.py` / `pagination.py`.  
> Field names match the backend. If drift appears, **Python schemas + `/docs` win**.

```ts
// Envelopes
type ApiResponse<T> = {
  success: true;
  data: T;
  message?: string | null;
};

type ErrorResponse = {
  success: false;
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
};

type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
};

// Query: page >= 1 (default 1), size 1..100 (default 20)

// Auth — src/auth/schemas.py
type UserOut = {
  id: string; // UUID
  email: string;
  name: string;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string; // ISO datetime
};

type AuthMeResponse = {
  is_guest: boolean;
  session_id: string;
  user: UserOut | null;
};

// Destinations — src/destinations/schemas.py
type DestinationOut = {
  id: string;
  name: string;
  country: string;
  display_name: string;
  lat: number;
  lng: number;
  place_count: number;
  created_at: string;
};

type DestinationReadinessOut = {
  destination_id: string;
  score: number;
  tier: "ready" | "limited" | "sparse";
  place_count: number;
  enriched_pct: number;
  indexed_pct: number;
  message: string | null;
};

// Places — src/places/schemas.py
type PlaceOut = {
  id: string;
  osm_id: string;
  name: string;
  category: string;
  tags: Record<string, unknown>;
  summary: string | null;
  lat: number;
  lng: number;
  destination_id: string;
  created_at: string;
};

// Planner — src/planner/schemas.py
type PlanRequest = {
  destination_id: string;
  raw_input: string; // min length 1
  days?: number | null;
  base_lat?: number | null;
  base_lng?: number | null;
  accommodation_label?: string | null; // display-only; not a Trip column
};

// Trips — src/trips/schemas.py
type TripStatus = "draft" | "complete" | "failed";

type TripPlaceOut = {
  id: string;
  place_id: string;
  day_number: number;
  order_in_day: number;
  travel_time_min: number;
  visit_duration_min: number;
  suggested_start_time: string | null;
  arrival_note: string | null;
  polyline: string | null;
  name: string | null;
  lat: number | null;
  lng: number | null;
};

type TripOut = {
  id: string;
  user_id: string | null;
  session_id: string;
  destination_id: string;
  days: number;
  preferences: Record<string, unknown>;
  status: TripStatus;
  created_at: string;
  updated_at: string;
  places: TripPlaceOut[]; // may be empty on list endpoints
};

type ReorderStopsIn = { place_ids: string[] };
type AddStopIn = { place_id: string };
```

---

## 15. GeoJSON map contract (`GET /trips/{id}/geojson`)

Itinerary overlay data for MapLibre (basemap tiles are MapTiler / OSM-dev — §2). Public raw GeoJSON (not `ApiResponse`). Built by `TripService.build_geojson`.

```ts
type TripGeoJson = {
  type: "FeatureCollection";
  features: Array<TripPointFeature | TripLineFeature>;
};

// Point — stop markers (coordinates are GeoJSON [lng, lat])
type TripPointFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] }; // [lng, lat]
  properties: {
    name: string | null;
    day: number;
    order: number;
    suggested_start_time: string | null;
    place_id: string;
    trip_place_id: string;
  };
};

// LineString — concatenated day legs when polylines decode
type TripLineFeature = {
  type: "Feature";
  geometry: { type: "LineString"; coordinates: [number, number][] };
  properties: {
    day: number;
    trip_id: string;
  };
};
```

MapLibre: use Point features for markers; LineString features for day routes. Missing polylines → points only (never invent coordinates).

---

## 16. Error codes & rate limits (UX)

### HTTP / JSON `ErrorResponse.code` (branch toasts on these)

| Code | Typical HTTP | When |
|------|--------------|------|
| `destination_not_ready` | 409 | Generate refused — not enough places |
| `not_found` | 404 | Unknown destination / place / trip |
| `unauthorized` | 401 | Missing/invalid auth where Required |
| `forbidden` | 403 | Ownership / claim failure |
| `rate_limit_exceeded` | 429 | Middleware or trip-edit limiter |
| `validation_error` | 422 | Bad query/body |
| `external_service_error` | 502 | Upstream geo/etc. |
| `llm_unavailable` | 503 | LLM gateway down |
| `db_unavailable` | 503 | DB health |
| `internal_error` | 500 | Unhandled |

Also handle non-JSON failures (network, CORS, proxy buffering on SSE).

### SSE terminal `error` codes

| Code | Meaning |
|------|---------|
| `generation_timeout` | Graph hit `PLANNER_GENERATION_TIMEOUT_SECONDS` |
| `graph_recursion_limit` | Recursion bound exceeded |

### UX-visible rate limits (defaults from settings / context)

| Route | Limit (default) |
|-------|-----------------|
| `GET /destinations/search` | **20/min/IP** |
| `POST /planner/generate` | **10/min** |
| Trip day-edit routes | **20/min** (trip-edit limiter) |
| Default API paths | 60/min (middleware default) |

Exact numbers are config-driven (`RATE_LIMIT_*` in settings); treat the table as UX guidance and re-check `/docs` or settings if limits feel wrong.

---

*Source decisions: OpenSpec changes `frontend-stack-guide`, `fe-api-contract-guide`, `fe-guide-map-tiles`. Input draft: `docs/fe_suggestins.md`.*
