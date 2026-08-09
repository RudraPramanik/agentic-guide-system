# Wandr — Frontend Blueprint v1.1 (Definitive)

> Production-minded Next.js client for the Wandr FastAPI API. Sibling repo (not monorepo). Failure-first phases. Every step ends with a proof.
>
> **This file is the single source of truth for frontend development** (principles, FE AGENT guardrails, resilience/UX contracts, phased F-steps) — the FE counterpart of `docs/blueprint_final.md` for the backend.
> **Wire contract (stack, endpoints, DTOs, SSE, GeoJSON):** `docs/FE_guide.md` — **unchanged, still canonical**. Backend itself is not being touched until FE is built and integrated; this version only tightens what the FE does with the contract as it stands today.
> **Backend / planner SSOT:** `docs/blueprint_final.md` (unchanged by this doc).

**Supersedes:** v1.0. This is a patch pass, not a redesign — v1.0's phase order, stack, and principles are retained. Changes are additive/clarifying, flagged inline with `🆕 v1.1`. Do not use any parallel draft (e.g. retired `front_blueprint_2.md`).

**Non-goals of this document:** implementing the Next.js app inside `guideagent`; changing FastAPI routes (backend stays frozen for this pass — see `docs/FE_guide.md` §11 OAuth gap); FE hosting/VPS SOP (`docs/steps/blueprint_production.md` is API-only).

---

## What changed vs v1.0 (read this first)

| # | Gap in v1.0 | Fix in v1.1 | Where |
|---|-------------|-------------|-------|
| 1 | Types hand-mirrored from `FE_guide.md` §14–15 with "schemas win on drift" as the only drift defense — the same failure mode already paid down once on DashNotes (`CURSOR_PROMPTS_UPDATE_v3.md` added mandatory OpenAPI type-locking) | New **F0.6 — OpenAPI type-lock step**: generate `types/generated/api.d.ts` from the live OpenAPI spec; hand types become a thin domain-mapping layer over generated ones, not the source of truth | F0.6 |
| 2 | Clarification round-trip (`clarification_needed`) had no re-submission contract — FE would have improvised | Explicit contract: re-POST `/generate` with clarification answer appended to `raw_input`, as a **new** stream (not resumed) | F3.3 |
| 3 | F2.2 left sparse-tier gating as "per product copy" — untestable | Pinned default: **warn + allow**, never hard-block guest generate, consistent with principle "guest path doesn't depend on polished login" | F2.2 |
| 4 | Rate-limit wording risked under-testing the live search limiter (critique draft called it unconfirmed) | **Corrected:** `GET /destinations/search` **20/min/IP is live** via `RateLimitMiddleware` + `RATE_LIMIT_DESTINATIONS_SEARCH_*`. FE debounces for UX and treats 429 as a real contract | F2.1 |
| 5 | `react-markdown` render target for LLM-authored narrative had no sanitization rule stated | AGENT.md hard rule: plain markdown only, no `rehype-raw`, no `dangerouslySetInnerHTML` | AGENT.md, F4.1 |
| 6 | Abort proof only checked that the client stopped reading, not that the server actually canceled generation | Added explicit cross-boundary proof in F3.2 / F7.3 | F3.2, F7.3 |
| 7 | Guest-session-mismatch 403 (locked backend rule, P6.1) was folded into generic 403 handling with generic copy | Added as its own failure-boundary row with dedicated copy | F4.1, F5.1, Failure Boundary Summary |
| 8 | No accessibility or mobile/responsive pass anywhere in the phases | Added F7.5 (a11y) and F7.6 (responsive/mobile) as named hardening steps, plus a running principle | Principles #14–15, F7.5, F7.6 |
| 9 | Narrative cache (Zustand, Option A) had no stated bound | Added to Deferred/known gaps as an explicit MVP tradeoff (unbounded but small; cap deferred) | Deferred / known gaps |

Everything else from v1.0 (phase order F0–F7, stack lock, cookie model, resilience contracts, LLD patterns) is retained as-is and not repeated with commentary below except where a row changed.

---

## Doc relationship

| Doc | Role |
|-----|------|
| `docs/FE_guide.md` | Locked stack + live API integration contract (what to call, envelopes, auth matrix, DTOs) — **not modified this pass** |
| **`docs/blueprint_frontend.md` (this file, v1.1)** | **Sole** FE build bible — principles, AGENT, fallbacks, proofs (counterpart of `blueprint_final.md` for backend) |
| `docs/blueprint_final.md` | Backend / planner development SSOT — **frozen until FE integration is done**, then revisited together |
| `docs/context.md` | Agent checkpoint (live endpoints, stubs) — not a FE phase tracker |

### Conflict rule (wire shapes)

| Priority | Source |
|----------|--------|
| 1 | Live routers + `src/*/schemas.py` |
| 2 | OpenAPI at `{API}/docs` — 🆕 v1.1: now also the **codegen source** for `types/generated/`, not just a manual reference |
| 3 | `docs/FE_guide.md` |
| 4 | **This blueprint** |

If this file disagrees with Python schemas or `FE_guide.md` on a public route/DTO, **schemas / FE_guide win**. Update the blueprint in the same change window.

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
| 8 | **Server state in Query; UI state thin** — Zustand for wizard / map selection / narrative cache only |
| 9 | **Controlled AI-assisted FE** — FE `AGENT.md` prevents uncontrolled Cursor output |
| 10 | **Envelope discipline** — one client parses success/error; branch pagination / GeoJSON / SSE / 204 |
| 11 | **Streams are abortable, end-to-end** — navigate-away cancels generate on the client *and* the server actually stops generating; not just "the reader stopped" 🆕 v1.1 |
| 12 | **Types follow the backend** — generated from OpenAPI, not hand-copied; domain types are a thin layer over generated ones 🆕 v1.1 |
| 13 | **Degrade the map, don't blank the trip** — missing polylines → points only; tile fail → list-first UI |
| 14 | **Never render untrusted content as raw HTML** — LLM-authored narrative renders as plain markdown only; no raw-HTML passthrough 🆕 v1.1 |
| 15 | **Usable without a mouse or a laptop** — keyboard nav + ARIA-live on SSE progress; layout works down to a phone viewport; both are hardening-phase deliverables, not afterthoughts 🆕 v1.1 |

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
- 🆕 Hand-written types in `types/` are a thin domain layer ONLY. The source of truth for wire shapes is `types/generated/api.d.ts` (generated from OpenAPI — see F0.6). Never hand-edit generated files; regenerate instead.

### Resilience / UX (non-negotiable)
- Every API `fetch` MUST accept an `AbortSignal` (or equivalent timeout abort).
- Mutations: no blind automatic retries. Idempotent GETs may use at most one bounded retry on network blip.
- Map `ErrorResponse.code` (and non-JSON failures) to user-visible toasts / panels — never infinite spinners.
- Rate limit `429` / `rate_limit_exceeded` → backoff messaging + brief CTA disable.
- Map tile / style failure MUST leave day list / trip detail usable (list-first).
- Missing GeoJSON LineStrings → render Point features only; never invent coordinates.
- 🆕 A 403 caused by guest-session mismatch (`wandr_session` cookie doesn't match `Trip.session_id`) MUST render distinct copy from a generic ownership 403 — see Failure Boundary Summary. Do not collapse both into one generic "forbidden" panel.

### Streaming (non-negotiable)
- Planner generate uses POST `fetch` + `ReadableStream` parsing of `event:` / `data:` frames.
- NEVER use browser `EventSource` for `/planner/generate` (GET-only).
- Abort the stream on unmount / navigate-away, using a real `AbortController` passed into `fetch` — this is what allows the backend's `request.is_disconnected()` poll to actually cancel the background task. A client that merely stops reading without aborting the underlying request leaves the server generating (and billing LLM tokens) needlessly.
- Do NOT auto-retry a full generate without explicit user action.
- Pre-stream HTTP 409 `destination_not_ready` is not SSE — route to readiness gate UI.
- Cache replay may omit `tool_*` events — treat as normal.
- After `itinerary_done`, navigate via `trip_id` then `GET /trips/{id}` (+ `/geojson`). Do not treat the full SSE blob as the long-term UI model.
- Narrative MVP (Option A): may cache day title/narrative from `itinerary_done` in session UI state keyed by `trip_id`; hard reload may lose prose. Do not invent a narrative API.
- 🆕 `clarification_needed` is terminal but NOT an error. On the user's answer, re-submit a **fresh** `POST /planner/generate` call with `raw_input` = original input + a newline + the answer. Do not attempt to "resume" the prior stream — there is no resume endpoint.

### Content rendering (non-negotiable) 🆕 v1.1
- LLM-authored day narrative (title/prose from `itinerary_done` / `GET /trips/{id}`) renders via `react-markdown` + `remark-gfm` ONLY.
- NEVER add `rehype-raw`, NEVER use `dangerouslySetInnerHTML` for narrative content, even for "just a little" custom formatting. Treat narrative text as untrusted.

### Code conventions
- TypeScript strict. Wire types generated from OpenAPI (`types/generated/`); domain types in `types/` compose/narrow them. Schemas win on drift — regenerate, don't patch by hand.
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

Aligned with `FE_guide.md` §12, plus the generated-types directory.

```
wandr-web/                    # sibling Next.js repo (name illustrative)
├── AGENT.md                  # ★ paste from this blueprint — before feature code
├── package.json
├── .env.example               # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_MAP_STYLE_URL
├── scripts/
│   └── generate-api-types.sh  # 🆕 v1.1 — pulls {API}/openapi.json → types/generated/api.d.ts
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
├── types/
│   ├── generated/
│   │   └── api.d.ts          # 🆕 v1.1 — generated, never hand-edited, regenerated in F0.6 and whenever backend DTOs change
│   └── *.ts                  # thin domain types composing generated types — mirrors FE_guide §14–15 as fallback narrative only
├── providers/                # QueryClient, theme, toaster
└── tests/                    # vitest + playwright (F7)
```

---

## Environment variables

### Frontend only (sibling `.env.local` / `.env.example`)

| Variable | Example | Notes |
|----------|---------|--------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API origin, no trailing slash. Also used by `scripts/generate-api-types.sh` to fetch `{API}/openapi.json`. |
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
| Backend contract | **Frozen for this build pass.** Any backend gap discovered while implementing FE (e.g. OAuth bounce, distinct `session_mismatch` error code) gets logged in "Deferred / known gaps" below, not silently worked around with FE guesses about backend behavior |

No competing SameSite / dual-session model in MVP.

---

## Resilience / UX Contracts

| Surface | Timeout / abort | Retry | Named fallback |
|---------|-----------------|-------|----------------|
| JSON API `fetch` | `AbortSignal`; default budget **15–30s** | Idempotent GET: at most **1** bounded retry on network blip; mutations: **none** | Toast / panel from `ErrorResponse.code`; empty state |
| Planner SSE | Abort on unmount via real `AbortController` (see AGENT.md streaming rules); respect backend ~**45s** generation ceiling | **No** auto-retry full generate | Error panel; 409 → readiness gate |
| Map style / tiles | MapLibre error handlers | OSM-compatible style **dev only** | Trip day list remains primary UI |
| GeoJSON overlay | Same as JSON API | — | Points only; "route unavailable" copy |
| `GET /auth/me` | Same as JSON API | 1 retry on network blip | Treat as guest; show reconnect |
| Rate limits | — | — | `rate_limit_exceeded` / 429 → Sonner + brief CTA disable — never infinite spin. Destination-search **20/min/IP is live** (`RateLimitMiddleware`); debounce client-side anyway; treat returned 429 as authoritative |
| Guest-session mismatch (🆕 v1.1) | — | — | 403 with copy distinct from generic ownership 403: "This trip belongs to a different session" — no retry, no login prompt (login wouldn't fix it) |

Error code catalog for toasts: **`FE_guide.md` §16**.

---

## Core design blocks

### API Gateway client + envelope adapters

- Single `lib/api/client.ts`: prefix `NEXT_PUBLIC_API_URL`, `credentials: "include"`, JSON parse, typed throws on `success: false` or non-OK HTTP.
- Adapters: `ApiResponse<T>`, bare `PaginatedResponse<T>`, raw GeoJSON, HTTP 204 empty, SSE (separate module).
- Domain modules: `auth`, `destinations`, `places`, `planner`, `trips` — map 1:1 to **`FE_guide.md` §8**.
- 🆕 Types used by the client come from `types/generated/api.d.ts` first; `types/*.ts` domain types narrow/compose them (e.g. discriminated unions for SSE events) rather than redeclaring fields.

### Abortable planner SSE

- `lib/sse/planner.ts`: POST `/api/v1/planner/generate`, parse `event:` / `data:` frames, driven by a real `AbortController` (not just stopping the reader loop).
- Progress vs terminal: **`FE_guide.md` §7**.
- Terminals: `itinerary_done` | `error` | `clarification_needed` (exactly one).
- On `itinerary_done`: persist narrative Option A into session store if present; navigate with `trip_id`.
- 🆕 On `clarification_needed`: render the clarification prompt; on the user's answer, call `generate()` again with a **new** `AbortController` and `raw_input = originalInput + "\n" + answer`. Treat it as a brand-new generation for progress-UI purposes (reset progress state).

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
| **Codegen type boundary** 🆕 | `types/generated/api.d.ts` ← OpenAPI, everything else composes it |

---

## Failure Boundary Summary

| Failure | Response |
|---------|----------|
| Network / CORS | Typed client error → toast "Can't reach API"; reconnect CTA |
| `destination_not_ready` 409 | No SSE; show readiness message / gate generate |
| `not_found` 404 | Empty / not-found panel for destination, place, or trip |
| `unauthorized` 401 | Prompt login for Required routes; keep guest flows working |
| `forbidden` 403 (ownership mismatch, authenticated user) | Ownership / claim failure copy; do not pretend success |
| `forbidden` 403 (guest session mismatch) 🆕 v1.1 | **Distinct copy**: "This trip belongs to a different session" — no login CTA (wouldn't help); this is the P6.1-locked guest-ownership rule, not a generic auth failure |
| `validation_error` 422 | Field-level or toast from `details` |
| `rate_limit_exceeded` 429 | Backoff toast; disable CTA briefly |
| `llm_unavailable` / `db_unavailable` 503 | "Service temporarily unavailable" |
| `internal_error` / 5xx | Generic failure; no stack traces in UI |
| SSE `generation_timeout` / `graph_recursion_limit` | Terminal error panel; allow retry by user |
| SSE `clarification_needed` | Show clarification UI; **on answer, fresh `/generate` call** (see AGENT.md streaming rules) — not a resume |
| Cache hit (no tool events) | Progress may jump to done — OK |
| Map tiles fail | List-first trip UI |
| Missing polylines | Points only |
| OAuth incomplete (API JSON page) | Documented CTA; guest path unaffected |
| Evaluation HTTP | **Do not call** — still stub on backend |
| Hard reload after generate | Narrative Option A may be gone; trip geometry still from GET |
| Client aborts SSE but server keeps generating 🆕 v1.1 | Should not happen if `AbortController` is wired correctly (see F3.2 proof) — if observed, it's a bug in the fetch/abort wiring, not an acceptable fallback state |

---

## Phase Blueprint

### Legend

- 📦 Package installed at this step
- 🏗️ LLD / FE pattern
- 🚨 Failure boundary
- ☁️ Production / env consideration
- 🔒 Resilience contract applied
- ✅ Proof (command or checklist)
- 🆕 New or materially changed vs v1.0

**Rule: no happy-path-only steps.** Every step below names pattern + failure + proof. Design for network failure, envelope errors, rate limits, SSE abort, empty readiness, ownership 403, and map degrade — not only search → generate → trip.

---

### F0 — Scaffold & core client
**~2.5 days · guest foundation** (was ~2 days; +0.5 day for F0.6)

#### 0.1 Sibling repo + directory skeleton
- Create Next.js App Router (TS strict) repo; folder tree as above (empty feature modules OK), including `types/generated/` and `scripts/`.
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
- Types imported from `types/generated/api.d.ts` where available (F0.6 must land before this is finalized — sequence 0.3 after 0.6, or stub with `FE_guide.md` §14 shapes and backfill)
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

#### 0.6 🆕 OpenAPI type-lock
> Closes the gap that DashNotes already taught us: hand-mirrored types drift silently. This step makes the wire-type boundary mechanical instead of a manual sync ritual.
- 📦 `openapi-typescript` (dev dependency)
- `scripts/generate-api-types.sh`: `npx openapi-typescript ${NEXT_PUBLIC_API_URL}/openapi.json -o types/generated/api.d.ts`
- Add `npm run gen:types` script wired to it; run once now against local API (requires backend running + at least `GET /openapi.json` reachable)
- Document in README: **rerun this after any backend DTO/route change** — treat it the same as `alembic upgrade head`, a required sync step, not optional
- `types/generated/api.d.ts` is gitignored-or-committed (commit it — reviewable diffs on drift are a feature, not noise)
- 🏗️ **Codegen type boundary**
- 🚨 API unreachable when generating → script fails loudly with a clear message ("start the backend first"), never silently writes an empty/stale file
- ✅ `npm run gen:types` → `types/generated/api.d.ts` populated; a deliberate backend schema change (add a field, run migration) → rerun → diff shows the new field, nothing hand-edited

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
- `GET /api/v1/destinations/search?q=` — `q` min length **2**
- 🆕 **Rate limit (live):** `GET /destinations/search` is limited to **20/min/IP** by `RateLimitMiddleware` (`RATE_LIMIT_DESTINATIONS_SEARCH_*` in settings) — same family as planner generate + trip-edit limits. Debounce input client-side (e.g. 300ms) for UX; on 429/`rate_limit_exceeded` show backoff toast + brief CTA disable. Proving a 429 under load is optional (manual/dev), not a flaky CI requirement.
- 🏗️ Domain module + Query
- 🚨 `q` < 2 → no request; 429 → backoff toast; empty list → empty UI
- ✅ Type "Da" → results or empty; debounce visibly reduces request count

#### 2.2 Readiness gate
- `GET /api/v1/destinations/{id}/readiness` → `tier` / `score` / `place_count` / `enriched_pct` / `indexed_pct` / `message`
- **No `search_available` field** on the wire — do not invent it
- 🆕 **Pinned default (was "per product copy" in v1.0):** `ready` → generate enabled, no warning. `limited` → generate enabled, inline warning using `message` from the API. `sparse` → generate **still enabled**, inline warning styled more prominently (e.g. amber vs neutral) — never hard-block. This matches the standing principle that guest generate must not depend on external gates beyond the 409 the backend itself enforces (`PLANNER_ABSOLUTE_MIN_PLACES`). If product later wants a hard block on `sparse`, that's a deliberate reversal of this default, not an ambiguity to resolve per-PR.
- 🏗️ **Null / empty UI**
- 🚨 404 destination → not-found
- ✅ Selecting a destination shows tier + message; generate CTA is enabled at every tier except the backend's own 409 floor

---

### F3 — Compose + planner SSE
**~2.5–3.5 days** (was ~2–3 days; +0.5 day for clarification loop + abort-integrity proof)

#### 3.1 Compose `PlanRequest`
- Fields: `destination_id`, `raw_input` (min 1), optional `days`, `base_lat`/`base_lng`, `accommodation_label`
- 🏗️ Form + Zod mirror of `FE_guide.md` §14 (typed against `types/generated/api.d.ts`)
- 🚨 Invalid client → no fetch
- ✅ Validation errors visible

#### 3.2 Abortable SSE client
- 📦 Motion (progress UI) at this step if used
- `lib/sse/planner.ts` — POST generate, frame parser, **real `AbortController`** wired into the `fetch` call (not just breaking the read loop)
- 🏗️ **Abortable Stream**
- 🔒 No EventSource; abort on unmount; no auto-retry
- 🚨 Non-SSE error body (409) detected before stream; parse failures → error panel
- ✅ Vitest: parse fixture frames; abort cancels reader
- 🆕 **End-to-end abort proof:** with the local API running, start a generate, abort mid-stream from the FE (navigate away or explicit cancel), and confirm server-side logs show the background task was canceled within a few seconds (not that it ran to completion in the background). This is a manual/dev-loop proof, not automatable in CI without backend log access, but it must be run and noted once before F3 is considered done — a client-only "the reader stopped" proof is not sufficient given the backend's `request.is_disconnected()` design depends on the connection actually closing.

#### 3.3 Progress UI + terminals
- Progress: `preferences_done`, `phase_changed`, `tool_*`, `validation_done`, …
- Terminals: `itinerary_done` → navigate `/trips/{trip_id}`; `error` → panel; `clarification_needed` → clarification UI (no trip)
- Cache hit: missing tool events OK
- **Narrative Option A:** on `itinerary_done`, store day title/narrative in Zustand/Query keyed by `trip_id` if present in payload
- 🆕 **Clarification re-submission contract:** on `clarification_needed`, render the question inline (not a modal that blocks the whole page — user should be able to see/edit their original input too). On answer submit, build `raw_input = originalRawInput + "\n" + answerText"` and call the generate SSE client again with a fresh `AbortController` and reset progress state. Do not attempt any form of stream resumption — there is no backend endpoint for that.
- 🚨 Timeout / `generation_timeout` / `graph_recursion_limit` → terminal error; user must re-submit
- ✅ Live or mocked stream updates UI; navigate only with `trip_id`; abort on leave; clarification → answer → fresh generate visibly restarts progress from zero

---

### F4 — Trip detail + MapLibre
**~2 days**

#### 4.1 Trip detail from API
- `GET /api/v1/trips/{id}` — Optional + ownership (`FE_guide.md` §8)
- Render days/stops from `TripOut.places`; preferences for summary chips
- Overlay session narrative from Option A cache if present; if missing after reload, omit prose (no fake text)
- Narrative prose renders via `react-markdown` + `remark-gfm` only — see AGENT.md content-rendering rule
- 🆕 403 handling is now two distinct panels, not one: authenticated-user-wrong-owner vs guest-session-mismatch (see Failure Boundary Summary). Both derive from the same HTTP 403 + `forbidden` code from the backend, so the FE must distinguish by context (is the viewer a guest or logged in?) rather than by response payload, since the backend doesn't currently differentiate the error body between the two cases (documented as a backend follow-up, not blocking).
- 🚨 403/404 → dedicated panels
- ✅ Open trip from generate; reload shows geometry without requiring narrative; guest-mismatch case shows the distinct copy

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
- 🆕 Distinguish claim-failure copy the same way as F4.1: session-mismatch vs already-claimed vs not-authenticated, rather than one generic "couldn't claim" toast
- 🚨 403/409 → clear copy; do not claim without login
- ☁️ Document: claim needs working login cookies; until `FRONTEND_URL` bounce, treat claim as best-effort on local Option A
- ✅ Claim succeeds when logged in with matching `wandr_session`; fails cleanly (and distinctly) otherwise

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
**~3–3.5 days** (was ~2 days; +1–1.5 days for a11y + responsive passes)

#### 7.1 Error-code toast map
- Central map from `FE_guide.md` §16 codes → copy, **including** the guest-session-mismatch 403 as a distinct entry (not folded into generic `forbidden`)
- 🚨 Unknown codes → generic message; log in dev
- ✅ Force 429/404/guest-mismatch-403 in mock → correct, distinct toast per case

#### 7.2 Unit tests
- 📦 Vitest + RTL
- Cover: envelope parsers, SSE frame parser, readiness gate helper (all three tiers), clarification re-submission builder, abort behavior
- ✅ `npm test` green

#### 7.3 Playwright smoke
- 📦 Playwright
- Path: search → readiness OK → generate (mock SSE or local API) → trip page renders
- 🆕 Add a second path: generate → mid-stream navigate-away → (against local API) confirm no orphaned trip is created / no `itinerary_done` arrives after navigation — closest CI-friendly proxy for the abort-integrity check from F3.2
- 🚨 Skip/fail clearly if API down — no flaky silent pass
- ✅ Smoke job documented in FE README

#### 7.4 Observability (optional)
- Sentry optional; PostHog deferred (`FE_guide.md` §2)
- 🚨 Telemetry MUST NOT send tokens or PII beyond what product allows
- ✅ No-op when DSN unset

#### 7.5 🆕 Accessibility pass
- Keyboard navigation through search → readiness → compose → generate → trip → edit, without a mouse
- `aria-live="polite"` region on SSE progress updates (phase/tool changes) so screen readers announce generation progress instead of silence until the terminal event
- Map: ensure trip day-list (not just the map) is the primary way to read itinerary content — already true by "list-first degrade," but confirm it's also true for a sighted-but-not-mouse-using or screen-reader user, not just a tile-failure fallback
- Focus management: modal/inline clarification UI traps focus appropriately and returns it on dismiss
- 🚨 Any interactive element unreachable by keyboard is a bug, not a "nice to have"
- ✅ Manual pass with keyboard-only + a screen reader (VoiceOver/NVDA) through the full happy path; document any gaps in Deferred / known gaps if not fixed this pass

#### 7.6 🆕 Responsive / mobile pass
- Layout audit at ~375px (small phone), ~768px (tablet), and desktop for: search, readiness card, compose form, generate progress, trip detail + map, edit UI
- Map behavior under 768px: collapse to a toggleable bottom sheet or tab, rather than squeezing a full map + full day-list into a narrow viewport simultaneously
- Touch targets sized appropriately for edit actions (reorder, remove, add stop)
- 🚨 No horizontal scroll on any core screen at 375px
- ✅ Manual pass (or Playwright viewport assertions) at the three breakpoints; document any deferred polish

---

## Package Install Order

| Step | Package | Reason |
|------|---------|--------|
| 0.1 | Next.js, React, TypeScript, ESLint | App scaffold |
| 0.4 | `@tanstack/react-query`, `sonner`, optional `next-themes` | Server state + toasts |
| 0.5 | Tailwind v4, shadcn/ui, `lucide-react` | UI primitives |
| 🆕 0.6 | `openapi-typescript` (dev) | Generate wire types from live OpenAPI spec |
| 2.1 / 3.1 | `react-hook-form`, `zod`, `@hookform/resolvers` | Forms |
| 3.2 | `motion` (if progress animation) | Generate UX |
| 4.1 | `react-markdown`, `remark-gfm` (optional) | Narrative prose only — no `rehype-raw` |
| 4.2 | `maplibre-gl` | Trip map |
| 0.x / 2.x | `zustand` | Thin UI store (wizard / narrative cache) |
| 0.x | `date-fns` | Dates when first needed |
| 7.2 | `vitest`, `@testing-library/react`, jsdom | Unit tests |
| 7.3 | `@playwright/test` | Smoke e2e |

**Rejected / deferred installs:** Redux, Better Auth, Vercel AI SDK (planner), Google Maps JS (primary), TanStack Table, Recharts — see `FE_guide.md` §3. `rehype-raw` is explicitly rejected, not just deferred — see AGENT.md content-rendering rule.

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
| 🆕 Distinct error body for guest-session-mismatch vs generic-ownership 403 | Backend follow-up | Both currently return the same `forbidden` code/shape; FE differentiates copy by client-side context (guest vs logged-in viewer) as a stopgap. A dedicated `code` (e.g. `session_mismatch`) would be cleaner — flag for the next backend pass. |
| 🆕 Narrative cache (Zustand, Option A) has no eviction/cap | Accepted MVP tradeoff | Small payloads (day titles + short prose), session-scoped, cleared on tab close. Acceptable for MVP; add a cap (e.g. LRU by trip_id, last N trips) if it ever becomes a real memory concern — not expected at MVP scale. |
| 🆕 Full a11y audit (automated, e.g. axe-core in CI) | Deferred beyond F7.5 | F7.5 is a manual pass sufficient to ship; wiring `axe-core` into Playwright is a nice-to-have for a later hardening round, not this build. |

---

## Timeline Summary (rough, non-binding)

| Phase | Days | Focus |
|-------|------|-------|
| F0 | 2.5 | Scaffold, AGENT, API client + type codegen, providers |
| F1 | 1 | Session shell |
| F2 | 1–2 | Search + readiness (pinned sparse-tier default) |
| F3 | 2.5–3.5 | Compose + SSE + clarification loop + abort-integrity proof |
| F4 | 2 | Trip + map |
| F5 | 1–2 | Claim + list |
| F6 | 2 | Day edit |
| F7 | 3–3.5 | Hardening / tests / a11y / responsive |
| **Total** | **~15.5–19 days** | FE only — assumes local API ready (was ~13–16 days in v1.0) |

---

## Quick Reference: What the FE MUST / MUST NOT do

| MUST | MUST NOT |
|------|----------|
| Use `credentials: "include"` on cookie calls | Store JWT in `localStorage` |
| Parse envelopes in one gateway client | Scatter ad-hoc `fetch` + `res.json()` |
| POST + ReadableStream for planner SSE | Use `EventSource` for generate |
| Abort streams on navigate-away with a real `AbortController` | Auto-retry full generate silently, or assume "stopped reading" = "server stopped" |
| Gate generate on readiness tier/message, allowing at every tier | Invent `search_available` on readiness, or hard-block on `sparse` |
| Prefer `GET /trips/{id}` after `trip_id` | Treat SSE blob as durable DB |
| Degrade map to list/points | Blank the whole trip on tile failure |
| Follow `FE_guide.md` auth matrix | Call evaluation HTTP or invent routes |
| Keep Zustand thin | Put server entities only in Redux/Zustand |
| Document OAuth gap in login UX | Block guest generate on polished login |
| Generate wire types from OpenAPI (`npm run gen:types`) | Hand-edit `types/generated/` |
| Render narrative via `react-markdown` only | Use `rehype-raw` or `dangerouslySetInnerHTML` on LLM text |
| Re-submit a fresh `/generate` call on clarification answers | Try to "resume" a terminated SSE stream |
| Give guest-session-mismatch 403s distinct copy | Show a login CTA for a 403 that login can't fix |

---

## Local verification loop (API + FE)

In **API** repo (`guideagent`): see `docs/context.md` / `FE_guide.md` §10 — compose, uvicorn, seed/enrich/index, CORS includes `http://localhost:3000`.

In **FE** repo:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

npm run gen:types   # 🆕 regenerate wire types against the running local API
npm run dev         # http://localhost:3000
```

Happy path proof: search → readiness OK → generate → open trip → map from `/geojson`.
Failure proofs: abort mid-SSE **and confirm server-side cancellation**; 409 readiness; tile URL broken; 401 on `/trips`; guest-session-mismatch 403 shows distinct copy; clarification answer triggers a fresh generate.

---

*Source: OpenSpec change `frontend-blueprint-v1-1` (promotes corrected v1.1). Stack/API contract: `docs/FE_guide.md`. Backend bible: `docs/blueprint_final.md` (frozen until FE integration, then revisited jointly).*