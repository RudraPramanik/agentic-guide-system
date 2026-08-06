## ADDED Requirements

### Requirement: Canonical frontend stack guide document

The project SHALL maintain `docs/FE_guide.md` as the canonical guide for Wandr’s separate Next.js frontend (sibling repo, not monorepo). The guide MUST define the locked MVP stack, deferred libraries, env-swappable API base URL rules, and FastAPI integration contracts so a production FE can be built by changing `NEXT_PUBLIC_API_URL` when the API host is ready.

#### Scenario: Guide exists and is discoverable

- **WHEN** an agent or developer starts frontend work
- **THEN** they MUST use `docs/FE_guide.md` as the stack source of truth (with `docs/fe_suggestins.md` treated as historical input only)

#### Scenario: Env-swappable API base

- **WHEN** the frontend is configured for local vs production
- **THEN** the only required FE host switch MUST be the public API base URL env (e.g. `NEXT_PUBLIC_API_URL`)
- **AND** the guide MUST forbid placing database, Redis, Qdrant, or LLM secrets in the frontend env

### Requirement: Locked MVP technology stack

`docs/FE_guide.md` MUST lock the MVP frontend stack to: Next.js App Router, TypeScript, Tailwind CSS v4, shadcn/ui, Lucide, Motion, React Hook Form + Zod, TanStack Query v5, Zustand for UI-only state, next-themes, Sonner, date-fns, and MapLibre GL with OSM-compatible tiles for trip GeoJSON.

#### Scenario: Core libraries listed

- **WHEN** a reader opens the locked stack section
- **THEN** each MVP library above MUST appear with a one-line role
- **AND** Redux, Better Auth, and Google Maps as primary map SDK MUST NOT be listed as MVP defaults

### Requirement: Deferred and rejected suggestions

The guide MUST explicitly defer or reject items from the generic AI SaaS draft that do not fit Wandr MVP: Vercel AI SDK as the primary planner client, chat-notebook UX kit as the product shell, TanStack Table / Recharts dashboards, WebSockets, file upload stacks (R2/S3/dropzone), Mermaid/LaTeX, and dual auth systems (Better Auth / NextAuth owning sessions).

#### Scenario: Planner streaming approach

- **WHEN** documenting planner generate streaming
- **THEN** the guide MUST require a custom POST `fetch` + SSE frame parser against `POST /api/v1/planner/generate`
- **AND** MUST state that native `EventSource` MUST NOT be used (POST-only endpoint)
- **AND** MUST state that Vercel AI SDK is optional/deferred, not the MVP planner client

### Requirement: FastAPI cookie and CORS integration rules

The guide MUST require all browser API calls that need session or auth to use `credentials: "include"`, rely on httpOnly `wandr_token` and `wandr_session` cookies set by FastAPI, and assume MVP Option A (frontend and API on the same registrable domain in production; local `localhost:3000` ↔ `localhost:8000` with CORS).

#### Scenario: Authenticated or guest session call

- **WHEN** the frontend calls a cookie-scoped endpoint (planner generate, `/auth/me`, trip claim, trip edits)
- **THEN** the client MUST send cookies via `credentials: "include"`
- **AND** MUST NOT persist access tokens in `localStorage` or readable JS cookies

#### Scenario: Production domain pairing

- **WHEN** documenting production deploy pairing
- **THEN** the guide MUST require `app.` + `api.` (or equivalent) under one registrable domain for `SameSite=Lax`
- **AND** MUST note that backend `CORS_ALLOWED_ORIGINS` MUST list the FE origin (backend env, not FE env)

### Requirement: Domain API client map

The guide MUST specify a typed API layer organized by Wandr domains — Auth, Destinations, Places, Planner, Trips — wrapping shared `ApiResponse` / `ErrorResponse` / `PaginatedResponse` parsing and TanStack Query hooks. Generic Chat/Notebook/Workspace API modules MUST NOT be prescribed for MVP.

#### Scenario: Module-to-endpoint mapping

- **WHEN** implementing the FE API layer
- **THEN** Destinations client MUST cover search + readiness
- **AND** Planner client MUST cover SSE generate
- **AND** Trips client MUST cover get/list/geojson/claim/delete and day edit routes
- **AND** Auth client MUST cover google start, me, logout

### Requirement: Wandr MVP screen model

The guide MUST describe the MVP product flow as destination search → readiness → compose preferences → generate progress (phase/tool SSE) → trip detail with map → optional auth claim and day edits — not a generic multi-turn chat notebook as the primary shell.

#### Scenario: Generate progress UI

- **WHEN** `POST /planner/generate` streams events
- **THEN** the UI MUST be able to render progress from non-terminal SSE events and complete on terminal `itinerary_done` (with `trip_id`), `error`, or `clarification_needed`

### Requirement: Local verification loop

The guide MUST document that local FE development uses API-repo `docker compose` (PostGIS + Qdrant) plus host `uvicorn`, seeded destination data, and Next.js on port 3000 with `NEXT_PUBLIC_API_URL=http://localhost:8000`.

#### Scenario: Local end-to-end readiness

- **WHEN** a developer follows the local loop section
- **THEN** they MUST see steps for compose up, API start, seed/enrich/index as needed, and FE env pointing at `:8000`

### Requirement: Known OAuth callback gap

The guide MUST document that Google OAuth callback currently completes on the API host (JSON + Set-Cookie) without redirecting to the Next.js app, and MUST mark a future backend `FRONTEND_URL` (or equivalent) redirect as a follow-up — not as an already-implemented FE capability.

#### Scenario: Login expectation

- **WHEN** a developer implements the login button
- **THEN** the guide MUST warn that polished post-login return-to-app requires a backend redirect follow-up
- **AND** MUST allow guest generate/trip/map paths to proceed without that follow-up
