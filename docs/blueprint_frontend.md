# Wandr — Frontend Blueprint v1.0 (Definitive)

> Production-minded Next.js client for the Wandr FastAPI API. Sibling repo (not monorepo). Failure-first phases. Every step ends with a proof.
>
> **This file is the single source of truth for frontend development** (principles, FE AGENT guardrails, resilience/UX contracts, phased F-steps).
> **Wire contract (stack, endpoints, DTOs, SSE, GeoJSON):** `docs/FE_guide.md`.
> **Backend / planner SSOT:** `docs/blueprint_final.md` (unchanged by this doc).

**Supersedes:** none (first FE bible). Input stack lock: `docs/FE_guide.md` (OpenSpec `frontend-stack-guide`, `fe-api-contract-guide`, `fe-guide-map-tiles`).

**Non-goals of this document:** implementing the Next.js app inside `guideagent`; changing FastAPI routes; FE hosting/VPS SOP (`docs/steps/blueprint_production.md` is API-only).

---

## Doc relationship

| Doc | Role |
|-----|------|
| `docs/FE_guide.md` | Locked stack + live API integration contract (what to call, envelopes, auth matrix, DTOs) |
| **`docs/blueprint_frontend.md`** | How to build the sibling FE in phases — principles, AGENT, fallbacks, proofs |
| `docs/blueprint_final.md` | Backend / planner development SSOT |
| `docs/context.md` | Agent checkpoint (live endpoints, stubs) — not a FE phase tracker |

### Conflict rule (wire shapes)

| Priority | Source |
|----------|--------|
| 1 | Live routers + `src/*/schemas.py` |
| 2 | OpenAPI at `{API}/docs` |
| 3 | `docs/FE_guide.md` |
| 4 | **This blueprint** |

If this file disagrees with Python schemas or `FE_guide.md` on a public route/DTO, **schemas / FE_guide win**. Update the blueprint in the same change window.

---

## What's in this version

| Lock | Decision |
|------|----------|
| Phases | **F0–F7** guest-first: scaffold → session → search/readiness → SSE generate → trip+map → claim/list → day edit → harden |
| Narrative MVP | **Option A** — capture day title/narrative from terminal `itinerary_done` into session UI state; hard reload may lose prose; `GET /trips/{id}` is geometry/schedule SoT |
| Auth | FastAPI cookies only; polished OAuth return **deferred** (`FRONTEND_URL` bounce) — do not block F0–F4 |
| FE AGENT | Copy-ready block **for sibling FE repo only** — backend root `AGENT.md` stays API-only |
| Stack | As locked in `FE_guide.md` §2 — do not re-pick here |
| Steps | Bible-only for MVP (no `docs/steps/fe/step*.md` sprawl yet) |

---

## Principles

| # | Principle |
|---|-----------|
| 1 | **Packages at point of use** — install only in the F-step that needs them |
| 2 | **Pattern named per step** — every design decision cites an FE/LLD pattern |
| 3 | **Failure boundary per step** — every external call / stream / tile load has a named fallback UI |
| 4 | **Env-swappable API** — same build; only `NEXT_PUBLIC_API_URL` (+ map style) changes |
| 5 | **Lightest viable package** — no Redux; no AI SDK as planner client; no BFF unless cookie pain proves it |
| 6 | **Trip is the durable artifact** — not a chat / notebook / workspace shell |
| 7 | **FastAPI owns auth** — FE is a cookie client only |
| 8 | **Server state in Query; UI state thin** — Zustand for wizard / map selection only |
| 9 | **Controlled AI-assisted FE** — FE `AGENT.md` prevents uncontrolled Cursor output |
| 10 | **Envelope discipline** — one client parses success/error; branch pagination / GeoJSON / SSE / 204 |
| 11 | **Streams are abortable** — navigate-away cancels generate; no zombie readers |
| 12 | **Types follow the backend** — do not invent fields (e.g. no `search_available` on readiness JSON) |
| 13 | **Degrade the map, don’t blank the trip** — missing polylines → points only; tile fail → list-first UI |

---

## AGENT.md — FE coding guardrails (sibling repo)

> **On FE repo scaffold (F0.1):** create `AGENT.md` at the **sibling Next.js repo root** with the content below.
>
> **Backend `guideagent/AGENT.md` remains API-only.** Do **not** merge these rules into the backend AGENT file.

```markdown
# AGENT.md — Wandr Frontend Coding Guardrails

## Hard rules — never violate, never simplify away

### Architecture
- All HTTP to the API goes through `lib/api/client.ts` (+ domain modules). Never scatter raw `fetch` with ad-hoc URLs.
- Every cookie-scoped call MUST use `credentials: "include"`.
- Do NOT store access tokens in `localStorage`, sessionStorage, or readable JS cookies.
- Server/async state: TanStack Query. Ephemeral UI (wizard, map selection, session narrative cache): thin Zustand only — never Redux.
- Feature folders (`features/auth`, `destinations`, `planner`, `trips`) over dumping everything in `components/`.
- FastAPI owns auth. No Better Auth / NextAuth session ownership in MVP.
- Do NOT invent endpoints, DTO fields, or evaluation HTTP clients. Follow `docs/FE_guide.md` + OpenAPI.

### Resilience / UX (non-negotiable)
- Every API `fetch` MUST accept an `AbortSignal` (or equivalent timeout abort).
- Mutations: no blind automatic retries. Idempotent GETs may use at most one bounded retry on network blip.
- Map `ErrorResponse.code` (and non-JSON failures) to user-visible toasts / panels — never infinite spinners.
- Rate limit `429` / `rate_limit_exceeded` → backoff messaging + brief CTA disable.
- Map tile / style failure MUST leave day list / trip detail usable (list-first).
- Missing GeoJSON LineStrings → render Point features only; never invent coordinates.

### Streaming (non-negotiable)
- Planner generate uses POST `fetch` + `ReadableStream` parsing of `event:` / `data:` frames.
- NEVER use browser `EventSource` for `/planner/generate` (GET-only).
- Abort the stream on unmount / navigate-away.
- Do NOT auto-retry a full generate without explicit user action.
- Pre-stream HTTP 409 `destination_not_ready` is not SSE — route to readiness gate UI.
- Cache replay may omit `tool_*` events — treat as normal.
- After `itinerary_done`, navigate via `trip_id` then `GET /trips/{id}` (+ `/geojson`). Do not treat the full SSE blob as the long-term UI model.
- Narrative MVP (Option A): may cache day title/narrative from `itinerary_done` in session UI state keyed by `trip_id`; hard reload may lose prose. Do not invent a narrative API.

### Code conventions
- TypeScript strict. Types mirror `FE_guide.md` §14–15; schemas win on drift.
- FE env: only `NEXT_PUBLIC_*` (API URL, map style). Never `DATABASE_URL`, `REDIS_*`, `LLM_*`, OAuth secrets.
- No new packages without package.json justification and installing at the F-step that needs them.
- Envelope exceptions: bare `PaginatedResponse`, raw GeoJSON, SSE frames, HTTP 204 — branch parsers; do not force `ApiResponse`.

### When in doubt
- Check Resilience / UX Contracts in `docs/blueprint_frontend.md`.
- Check live auth matrix in `docs/FE_guide.md` §8.
- Prefer empty/error UI over fake data.
```

---

## Project structure (sibling FE repo)

Aligned with `FE_guide.md` §12. Create the tree in F0; fill modules at the phase that needs them.

```
wandr-web/                    # sibling Next.js repo (name illustrative)
├── AGENT.md                  # ★ paste from this blueprint — before feature code
├── package.json
├── .env.example              # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_MAP_STYLE_URL
├── app/                      # App Router routes
│   ├── layout.tsx
│   ├── page.tsx              # search entry
│   ├── generate/
│   ├── trips/
│   │   └── [id]/
│   └── auth/                 # done / error placeholders for future bounce
├── components/
│   ├── ui/                   # shadcn
│   ├── map/
│   └── generate/             # SSE progress
├── features/
│   ├── auth/
│   ├── destinations/
│   ├── planner/
│   └── trips/
├── hooks/
├── lib/
│   ├── api/
│   │   ├── client.ts         # ★ gateway + envelopes
│   │   ├── auth.ts
│   │   ├── destinations.ts
│   │   ├── places.ts
│   │   ├── planner.ts
│   │   └── trips.ts
│   ├── sse/
│   │   └── planner.ts        # Abortable stream parser
│   └── utils/
├── store/                    # zustand — wizard, map selection, narrative cache
├── types/                    # mirrors FE_guide §14–15
├── providers/                # QueryClient, theme, toaster
└── tests/                    # vitest + playwright (F7)
```

---

## Environment variables

### Frontend only (sibling `.env.local` / `.env.example`)

| Variable | Example | Notes |
|----------|---------|--------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API origin, no trailing slash |
| `NEXT_PUBLIC_MAP_STYLE_URL` | MapTiler style JSON URL | Recommended staging/prod basemap |

Details and forbidden secrets: **`FE_guide.md` §4**. Never put DB/Redis/LLM/OAuth secrets in the FE.

### Backend must match FE host (configured on API — not in Next)

See **`FE_guide.md` §4–5**: `CORS_ALLOWED_ORIGINS` includes FE origin (never `*` with cookies); Google OAuth redirect URIs; Option A same registrable domain for prod cookies.

---

## Deployment / cookie decisions (LOCKED)

| Decision | Lock |
|----------|------|
| Cookie model | **Option A** — `app.` + `api.` under same registrable domain; `SameSite=Lax` |
| FE transport | Direct browser → API + CORS (no Next BFF in MVP) |
| OAuth return | **Deferred** — API callback still returns JSON on API host (`FE_guide.md` §11). Guest path F0–F4 does not depend on polished login |
| Production API proxy | Must not buffer `/api/v1/planner/generate` (see production blueprint) |

No competing SameSite / dual-session model in MVP.

---

## Resilience / UX Contracts

| Surface | Timeout / abort | Retry | Named fallback |
|---------|-----------------|-------|----------------|
| JSON API `fetch` | `AbortSignal`; default budget **15–30s** | Idempotent GET: at most **1** bounded retry on network blip; mutations: **none** | Toast / panel from `ErrorResponse.code`; empty state |
| Planner SSE | Abort on unmount; respect backend ~**45s** generation ceiling | **No** auto-retry full generate | Error panel; 409 → readiness gate |
| Map style / tiles | MapLibre error handlers | OSM-compatible style **dev only** | Trip day list remains primary UI |
| GeoJSON overlay | Same as JSON API | — | Points only; “route unavailable” copy |
| `GET /auth/me` | Same as JSON API | 1 retry on network blip | Treat as guest; show reconnect |
| Rate limits | — | — | `rate_limit_exceeded` / 429 → Sonner + brief CTA disable — never infinite spin |

Error code catalog for toasts: **`FE_guide.md` §16**.

---

## Core design blocks

### API Gateway client + envelope adapters

- Single `lib/api/client.ts`: prefix `NEXT_PUBLIC_API_URL`, `credentials: "include"`, JSON parse, typed throws on `success: false` or non-OK HTTP.
- Adapters: `ApiResponse<T>`, bare `PaginatedResponse<T>`, raw GeoJSON, HTTP 204 empty, SSE (separate module).
- Domain modules: `auth`, `destinations`, `places`, `planner`, `trips` — map 1:1 to **`FE_guide.md` §8**.

### Abortable planner SSE

- `lib/sse/planner.ts`: POST `/api/v1/planner/generate`, parse `event:` / `data:` frames.
- Progress vs terminal: **`FE_guide.md` §7**.
- Terminals: `itinerary_done` | `error` | `clarification_needed` (exactly one).
- On `itinerary_done`: persist narrative Option A into session store if present; navigate with `trip_id`.

### MapLibre + GeoJSON degrade

- Client Component map; data from `GET /trips/{id}/geojson` (**`FE_guide.md` §15**).
- Point → markers; LineString → day routes; missing lines → points only.
- Tile failure → hide/collapse map, keep itinerary list.

### TanStack Query keys / invalidation

| Key (illustrative) | Invalidate on |
|--------------------|---------------|
| `["auth","me"]` | login/logout (when bounce works); after claim if `/me` shape changes |
| `["destinations","search", q]` | — (short staleTime OK) |
| `["destinations","readiness", id]` | before generate |
| `["trips","list"]` | claim, delete |
| `["trips", id]` | any day-edit mutation, claim |
| `["trips", id, "geojson"]` | day-edit mutations that change geometry |

---

## LLD / FE Pattern Reference

| Pattern | Where used |
|---------|------------|
| **API Gateway client** | `lib/api/client.ts` |
| **Domain modules** | `lib/api/{auth,destinations,places,planner,trips}.ts` |
| **Envelope Adapter** | success / error / pagination / geojson / sse parsers |
| **Abortable Stream** | `lib/sse/planner.ts` |
| **Server-state cache** | TanStack Query keys + invalidation |
| **Thin UI store** | Zustand wizard / map / narrative cache |
| **Null / empty UI** | sparse readiness, empty trip list, map no-lines |
| **Cookie session probe** | `GET /auth/me` |
| **Feature folders** | `features/*` |
| **List-first degrade** | trip page when tiles fail |

---

## Failure Boundary Summary

| Failure | Response |
|---------|----------|
| Network / CORS | Typed client error → toast “Can’t reach API”; reconnect CTA |
| `destination_not_ready` 409 | No SSE; show readiness message / gate generate |
| `not_found` 404 | Empty / not-found panel for destination, place, or trip |
| `unauthorized` 401 | Prompt login for Required routes; keep guest flows working |
| `forbidden` 403 | Ownership / claim failure copy; do not pretend success |
| `validation_error` 422 | Field-level or toast from `details` |
| `rate_limit_exceeded` 429 | Backoff toast; disable CTA briefly |
| `llm_unavailable` / `db_unavailable` 503 | “Service temporarily unavailable” |
| `internal_error` / 5xx | Generic failure; no stack traces in UI |
| SSE `generation_timeout` / `graph_recursion_limit` | Terminal error panel; allow retry by user |
| SSE `clarification_needed` | Show clarification UI; no trip navigation |
| Cache hit (no tool events) | Progress may jump to done — OK |
| Map tiles fail | List-first trip UI |
| Missing polylines | Points only |
| OAuth incomplete (API JSON page) | Documented CTA; guest path unaffected |
| Evaluation HTTP | **Do not call** — still stub on backend |
| Hard reload after generate | Narrative Option A may be gone; trip geometry still from GET |

---

## Phase Blueprint

### Legend

- 📦 Package installed at this step
- 🏗️ LLD / FE pattern
- 🚨 Failure boundary
- ☁️ Production / env consideration
- 🔒 Resilience contract applied
- ✅ Proof (command or checklist)

**Rule: no happy-path-only steps.** Every step below names pattern + failure + proof. Design for network failure, envelope errors, rate limits, SSE abort, empty readiness, ownership 403, and map degrade — not only search → generate → trip.

---

### F0 — Scaffold & core client
**~2 days · guest foundation**

#### 0.1 Sibling repo + directory skeleton
- Create Next.js App Router (TS strict) repo; folder tree as above (empty feature modules OK).
- Write `AGENT.md` from this blueprint **before** feature screens.
- 🏗️ **Feature folders** + Modular UI shell
- 🚨 Wrong package manager lockfile / Node version → document engines in README
- ✅ Tree exists; `AGENT.md` present at FE root; `npm run build` or `dev` boots empty app

#### 0.2 Env example + API URL
- 📦 (from create-next-app) — no extra yet
- `.env.example` with `NEXT_PUBLIC_API_URL`, optional `NEXT_PUBLIC_MAP_STYLE_URL`
- ☁️ Same build for local/prod — only URL changes
- 🚨 Missing `NEXT_PUBLIC_API_URL` → client throws clear config error (no silent `undefined` fetches)
- ✅ `console` / health call uses configured origin

#### 0.3 `lib/api/client.ts` — Gateway + envelopes
- Implement `ApiResponse` / `ErrorResponse` parsers; helpers for pagination, 204, raw JSON
- Types from `FE_guide.md` §14 (illustrative mirrors)
- 🏗️ **API Gateway** + **Envelope Adapter**
- 🔒 AbortSignal on all calls; credentials include
- 🚨 Non-JSON body / network → typed `NetworkError`; `success: false` → typed `ApiError(code)`
- ✅ Unit-testable parse of success + error fixtures; `GET {API}/api/v1/health` smoke

#### 0.4 Providers — Query + toaster (+ optional theme)
- 📦 `@tanstack/react-query`, `sonner`, optional `next-themes`
- 🏗️ **Server-state cache** provider at root layout
- 🚨 Query errors bubble to toast boundary — no unhandled rejection spam
- ✅ App loads with QueryClientDevtools optional in dev

#### 0.5 shadcn/ui + Tailwind baseline
- 📦 Tailwind v4, shadcn primitives, Lucide as needed
- 🚨 Do not invent a second design system
- ✅ Button / toast render on a scratch page

---

### F1 — Session shell
**~1 day**

#### 1.1 `lib/api/auth.ts` + `useAuthMe`
- `GET /api/v1/auth/me` → `AuthMeResponse` (`FE_guide.md` §8, §14)
- 🏗️ **Cookie session probe**
- 🔒 1 retry on network blip; else treat as guest + reconnect
- 🚨 401/5xx → guest UI, not crash
- ✅ Guest session_id set (cookie visible in Network as httpOnly); UI shows Guest

#### 1.2 Login CTA + logout
- Login: navigate to `GET {API}/api/v1/auth/google`
- Logout: `POST /api/v1/auth/logout` with credentials; invalidate `["auth","me"]`
- 🚨 **OAuth gap:** success may leave user on API JSON page (`FE_guide.md` §11). CTA helper text: login return incomplete until `FRONTEND_URL` bounce
- ✅ Logout clears `wandr_token` (session cookie may remain — expected); `/me` returns guest

#### 1.3 Shell chrome
- Minimal header: brand, guest/user chip, login/logout
- 🚨 Do not block browsing destinations while guest
- ✅ Search entry reachable while guest

---

### F2 — Destinations search + readiness
**~1–2 days**

#### 2.1 Destination search
- 📦 RHF + Zod if not already (compose later may share)
- `GET /api/v1/destinations/search?q=` — `q` min length **2**; rate limit **20/min/IP**
- 🏗️ Domain module + Query
- 🚨 `q` &lt; 2 → no request; 429 → backoff toast; empty list → empty UI
- ✅ Type “Da” → results or empty; throttle UX ok

#### 2.2 Readiness gate
- `GET /api/v1/destinations/{id}/readiness` → `tier` / `score` / `place_count` / `enriched_pct` / `indexed_pct` / `message`
- **No `search_available` field** on the wire — do not invent it
- Branch: `ready` | `limited` | `sparse` (disable or warn generate for sparse per product copy)
- 🏗️ **Null / empty UI**
- 🚨 404 destination → not-found; low tier → block or confirm with message
- ✅ Selecting a destination shows tier + message; generate CTA respects gate

---

### F3 — Compose + planner SSE
**~2–3 days**

#### 3.1 Compose `PlanRequest`
- Fields: `destination_id`, `raw_input` (min 1), optional `days`, `base_lat`/`base_lng`, `accommodation_label`
- 🏗️ Form + Zod mirror of `FE_guide.md` §14
- 🚨 Invalid client → no fetch
- ✅ Validation errors visible

#### 3.2 Abortable SSE client
- 📦 Motion (progress UI) at this step if used
- `lib/sse/planner.ts` — POST generate, frame parser, AbortController
- 🏗️ **Abortable Stream**
- 🔒 No EventSource; abort on unmount; no auto-retry
- 🚨 Non-SSE error body (409) detected before stream; parse failures → error panel
- ✅ Vitest: parse fixture frames; abort cancels reader

#### 3.3 Progress UI + terminals
- Progress: `preferences_done`, `phase_changed`, `tool_*`, `validation_done`, …
- Terminals: `itinerary_done` → navigate `/trips/{trip_id}`; `error` → panel; `clarification_needed` → clarification UI (no trip)
- Cache hit: missing tool events OK
- **Narrative Option A:** on `itinerary_done`, store day title/narrative in Zustand/Query keyed by `trip_id` if present in payload
- 🚨 Timeout / `generation_timeout` / `graph_recursion_limit` → terminal error; user must re-submit
- ✅ Live or mocked stream updates UI; navigate only with `trip_id`; abort on leave

---

### F4 — Trip detail + MapLibre
**~2 days**

#### 4.1 Trip detail from API
- `GET /api/v1/trips/{id}` — Optional + ownership (`FE_guide.md` §8)
- Render days/stops from `TripOut.places`; preferences for summary chips
- Overlay session narrative from Option A cache if present; if missing after reload, omit prose (no fake text)
- 🚨 403/404 → dedicated panels
- ✅ Open trip from generate; reload shows geometry without requiring narrative

#### 4.2 GeoJSON + MapLibre
- 📦 `maplibre-gl` (+ types); MapTiler style URL
- `GET /trips/{id}/geojson` — raw FeatureCollection
- 🏗️ **List-first degrade**
- 🔒 Points-only if no LineStrings; tile error → collapse map
- 🚨 Never invent lat/lng; OSM tiles **dev only**
- ✅ Markers for stops; line when present; kill style URL → list still works

---

### F5 — Claim & trip list
**~1–2 days**

#### 5.1 My trips list
- `GET /api/v1/trips` — **Required** auth; bare paginated
- 🚨 401 → login CTA (acknowledge OAuth gap); empty → empty UI
- ✅ Authenticated user sees list (local cookie path)

#### 5.2 Claim trip
- `POST /api/v1/trips/{id}/claim` — Required; session must match; unclaimed only
- Invalidate trip + list queries
- 🚨 403/409 → clear copy; do not claim without login
- ☁️ Document: claim needs working login cookies; until `FRONTEND_URL` bounce, treat claim as best-effort on local Option A
- ✅ Claim succeeds when logged in with matching `wandr_session`; fails cleanly otherwise

#### 5.3 Delete trip (auth)
- `DELETE /api/v1/trips/{id}` — Required; HTTP **204**
- 🚨 No anonymous delete; 403/404 handling
- ✅ 204 → remove from list cache

---

### F6 — Day edit
**~2 days**

#### 6.1 Edit mutations
- Routes: reorder / add / remove / reoptimize — **Required + owner** (`FE_guide.md` §8)
- Bodies: `ReorderStopsIn`, `AddStopIn`
- 🏗️ Query invalidation on `["trips", id]` + geojson key
- 🔒 No blind retry on mutations
- 🚨 403 / 409 conflict / 422 validation / 429 trip-edit limit → toasts; rollback optimistic UI if used
- ✅ Each edit updates trip view; geojson refresh when geometry changes

#### 6.2 Places picker for add-stop
- `GET /api/v1/places?destination_id=` paginated; `GET /places/{id}` as needed
- 🚨 Unknown destination 404; empty page OK
- ✅ Add stop from list; duplicate conflict surfaced

---

### F7 — Hardening
**~2 days**

#### 7.1 Error-code toast map
- Central map from `FE_guide.md` §16 codes → copy
- 🚨 Unknown codes → generic message; log in dev
- ✅ Force 429/404 in mock → correct toast

#### 7.2 Unit tests
- 📦 Vitest + RTL
- Cover: envelope parsers, SSE frame parser, readiness gate helper, abort behavior
- ✅ `npm test` green

#### 7.3 Playwright smoke
- 📦 Playwright
- Path: search → readiness OK → generate (mock SSE or local API) → trip page renders
- 🚨 Skip/fail clearly if API down — no flaky silent pass
- ✅ Smoke job documented in FE README

#### 7.4 Observability (optional)
- Sentry optional; PostHog deferred (`FE_guide.md` §2)
- 🚨 Telemetry MUST NOT send tokens or PII beyond what product allows
- ✅ No-op when DSN unset

---

## Package Install Order

| Step | Package | Reason |
|------|---------|--------|
| 0.1 | Next.js, React, TypeScript, ESLint | App scaffold |
| 0.4 | `@tanstack/react-query`, `sonner`, optional `next-themes` | Server state + toasts |
| 0.5 | Tailwind v4, shadcn/ui, `lucide-react` | UI primitives |
| 2.1 / 3.1 | `react-hook-form`, `zod`, `@hookform/resolvers` | Forms |
| 3.2 | `motion` (if progress animation) | Generate UX |
| 4.1 | `react-markdown`, `remark-gfm` (optional) | Narrative prose only |
| 4.2 | `maplibre-gl` | Trip map |
| 0.x / 2.x | `zustand` | Thin UI store (wizard / narrative cache) |
| 0.x | `date-fns` | Dates when first needed |
| 7.2 | `vitest`, `@testing-library/react`, jsdom | Unit tests |
| 7.3 | `@playwright/test` | Smoke e2e |

**Rejected / deferred installs:** Redux, Better Auth, Vercel AI SDK (planner), Google Maps JS (primary), TanStack Table, Recharts — see `FE_guide.md` §3.

---

## Deferred / known gaps

| Item | Status | Notes |
|------|--------|-------|
| API `FRONTEND_URL` OAuth bounce | Backend follow-up | Unblocks polished login → app return |
| Persist day narrative on `TripOut` / prefs | Backend follow-up | Removes Option A reload loss |
| Evaluation HTTP UI | Blocked | Backend evaluation HTTP still stub — do not invent |
| Next.js BFF / rewrites | Deferred | Unless cookie pain appears |
| Google Maps primary SDK | Deferred | MapLibre locked |
| Vercel AI SDK chat surface | Deferred | Not MVP planner client |
| Admin dashboards / uploads / WebSockets | Deferred | No APIs |

---

## Timeline Summary (rough, non-binding)

| Phase | Days | Focus |
|-------|------|-------|
| F0 | 2 | Scaffold, AGENT, API client, providers |
| F1 | 1 | Session shell |
| F2 | 1–2 | Search + readiness |
| F3 | 2–3 | Compose + SSE |
| F4 | 2 | Trip + map |
| F5 | 1–2 | Claim + list |
| F6 | 2 | Day edit |
| F7 | 2 | Hardening / tests |
| **Total** | **~13–16 days** | FE only — assumes local API ready |

---

## Quick Reference: What the FE MUST / MUST NOT do

| MUST | MUST NOT |
|------|----------|
| Use `credentials: "include"` on cookie calls | Store JWT in `localStorage` |
| Parse envelopes in one gateway client | Scatter ad-hoc `fetch` + `res.json()` |
| POST + ReadableStream for planner SSE | Use `EventSource` for generate |
| Abort streams on navigate-away | Auto-retry full generate silently |
| Gate generate on readiness tier/message | Invent `search_available` on readiness |
| Prefer `GET /trips/{id}` after `trip_id` | Treat SSE blob as durable DB |
| Degrade map to list/points | Blank the whole trip on tile failure |
| Follow `FE_guide.md` auth matrix | Call evaluation HTTP or invent routes |
| Keep Zustand thin | Put server entities only in Redux/Zustand |
| Document OAuth gap in login UX | Block guest generate on polished login |

---

## Local verification loop (API + FE)

In **API** repo (`guideagent`): see `docs/context.md` / `FE_guide.md` §10 — compose, uvicorn, seed/enrich/index, CORS includes `http://localhost:3000`.

In **FE** repo:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev   # http://localhost:3000
```

Happy path proof: search → readiness OK → generate → open trip → map from `/geojson`.  
Failure proofs: abort mid-SSE; 409 readiness; tile URL broken; 401 on `/trips`.

---

*Source: OpenSpec change `frontend-blueprint`. Stack/API contract: `docs/FE_guide.md`. Backend bible: `docs/blueprint_final.md`.*
