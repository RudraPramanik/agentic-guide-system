## ADDED Requirements

### Requirement: OpenAPI wire-type lock
The frontend blueprint MUST include an F0 step (e.g. F0.6) that generates TypeScript wire types from the live OpenAPI document (`{API}/openapi.json`) into a generated path (e.g. `types/generated/api.d.ts`) using a documented script (e.g. `npm run gen:types` / `openapi-typescript`).

Hand-written types under `types/` MUST be a thin domain layer that composes or narrows generated types. Generated files MUST NOT be hand-edited; regenerate on backend DTO/route changes. SSE event discriminated unions MAY remain hand-authored overlays because stream frames are often under-specified in OpenAPI.

The FE AGENT block MUST state that generated OpenAPI types are the wire source of truth for JSON routes.

#### Scenario: Type regen is mechanical
- **WHEN** an implementer runs the documented type-generation script against a running local API
- **THEN** `types/generated/api.d.ts` is populated and a deliberate schema field addition appears in the regen diff without hand-editing generated files

#### Scenario: SSE overlay allowed
- **WHEN** the blueprint describes planner SSE event typing
- **THEN** it permits domain-layer unions for SSE frames rather than requiring full OpenAPI coverage of every `event:` name

### Requirement: Clarification re-submission contract
The frontend blueprint MUST define `clarification_needed` as a terminal (non-error) outcome that does **not** navigate to a trip. On user answer, the FE MUST issue a **fresh** `POST /api/v1/planner/generate` with a new `AbortController` and reset progress UI.

MVP default body rule: `raw_input` MUST equal the original compose input plus a newline plus the clarification answer. The blueprint MUST forbid inventing a stream-resume endpoint or treating clarification as an in-place continuation of the prior SSE connection.

#### Scenario: Clarification triggers fresh generate
- **WHEN** the stream terminates with `clarification_needed` and the user submits an answer
- **THEN** the FE starts a new generate request (not a resumed reader) with appended `raw_input` and progress reset from zero

### Requirement: End-to-end SSE abort integrity
The frontend blueprint MUST require that planner generate abort uses a real `AbortController` passed into `fetch` so the HTTP connection closes and the backend `request.is_disconnected()` poll can cancel work. Merely stopping the client reader loop without aborting the request MUST be documented as insufficient.

F3 (or equivalent) MUST include a proof that abort cancels server-side generation (manual/dev-loop against local API logs is acceptable). F7 Playwright smoke MUST include a navigate-away mid-stream path as a CI-friendly proxy where feasible.

#### Scenario: Abort closes the request
- **WHEN** the user navigates away or cancels mid-generate
- **THEN** the FE aborts the underlying fetch and the blueprint’s proof criteria require evidence the server did not continue generation to completion needlessly

### Requirement: Pinned sparse-tier generate default
The frontend blueprint MUST pin readiness gating defaults: `ready` enables generate; `limited` enables generate with inline warning from API `message`; `sparse` enables generate with a more prominent warning. The FE MUST NOT hard-block generate on `sparse`. The backend `409 destination_not_ready` floor remains the authoritative hard gate.

#### Scenario: Sparse still allows generate
- **WHEN** readiness tier is `sparse`
- **THEN** the generate CTA remains enabled with a prominent warning, and only a backend 409 disables the stream path

### Requirement: Guest-session-mismatch distinct UX
The frontend blueprint MUST treat guest-session-mismatch ownership failures as distinct from authenticated ownership failures in user-visible copy, even when the API currently returns the same `forbidden` / 403 body.

Guest-session-mismatch copy MUST NOT prompt login as the fix. Until the backend exposes a dedicated error code, the FE MAY differentiate by viewer context (guest vs authenticated) and MUST list a dedicated backend error code as a Deferred follow-up.

#### Scenario: Guest mismatch copy
- **WHEN** a guest receives 403 because `wandr_session` does not match the trip’s session
- **THEN** the UI shows distinct “different session” messaging without a login CTA that cannot fix the mismatch

### Requirement: LLM narrative markdown sanitization
The FE AGENT block and trip/narrative steps MUST require rendering LLM-authored day title/narrative via `react-markdown` with `remark-gfm` only. The blueprint MUST forbid `rehype-raw` and `dangerouslySetInnerHTML` for narrative content.

#### Scenario: No raw HTML passthrough
- **WHEN** narrative prose is rendered from SSE Option A cache or trip payloads
- **THEN** it is rendered as sanitized markdown without raw-HTML plugins or innerHTML injection

### Requirement: Accessibility and responsive hardening steps
The Phase Blueprint F7 (hardening) MUST include named steps for:

1. Accessibility — keyboard navigation through the core happy path; `aria-live` (or equivalent) for SSE progress; focus management for clarification UI; list-first itinerary readable without relying on the map alone.
2. Responsive / mobile — layout audit at small-phone, tablet, and desktop breakpoints; map collapses or toggles on narrow viewports; no horizontal scroll on core screens at ~375px.

Full automated axe-core CI MAY remain deferred beyond the manual F7 pass.

#### Scenario: Hardening names a11y and mobile
- **WHEN** an implementer reads F7
- **THEN** they find explicit a11y and responsive proof criteria, not only unit/e2e/error-map tasks

### Requirement: Single FE bible file
After this change, `docs/blueprint_frontend.md` MUST be the only FE phased-build SSOT. `docs/front_blueprint_2.md` MUST be removed or reduced to a stub that points solely at `docs/blueprint_frontend.md`. Agents MUST NOT be instructed to treat the critique draft as authoritative.

#### Scenario: No dual bible
- **WHEN** an implementer searches docs for the frontend blueprint
- **THEN** they find one authoritative phased bible at `docs/blueprint_frontend.md`

## MODIFIED Requirements

### Requirement: FE AGENT guardrails are separate from backend AGENT.md
The frontend blueprint MUST provide a complete FE `AGENT.md` content block for the sibling Next.js repo. Backend root `AGENT.md` MUST NOT be rewritten to include FE rules.

FE hard rules MUST include at least:

- API access only via shared `lib/api` client (`credentials: "include"`)
- No tokens in `localStorage` / readable cookies
- Planner streaming only via POST `fetch` + ReadableStream (never `EventSource`)
- Abort generate with a real `AbortController` passed into `fetch` (not reader-stop alone)
- Server state via TanStack Query; Zustand only for ephemeral UI (wizard / map / narrative cache)
- Wire types for JSON routes generated from OpenAPI; domain types compose/narrow; do not invent endpoints or DTO fields
- Clarification answers re-submit a fresh `/planner/generate` (no resume)
- LLM narrative: `react-markdown` + `remark-gfm` only — no `rehype-raw` / `dangerouslySetInnerHTML`
- Guest-session-mismatch 403 gets distinct copy (no useless login CTA)
- No DB/Redis/LLM secrets in FE env
- Envelope parsing centralized; branch for pagination / GeoJSON / SSE / 204
- Packages added only at the step that needs them, with justification

#### Scenario: FE AGENT is copy-ready
- **WHEN** scaffolding the sibling FE repo
- **THEN** an engineer can paste the blueprint’s AGENT block into FE-repo `AGENT.md` without inventing rules

### Requirement: Phased F-blueprint covers MVP product shell
The Phase Blueprint MUST cover, in dependency order, at least:

| Phase | Focus |
|-------|--------|
| F0 | Scaffold, AGENT.md, env, shared API client + envelopes, providers, OpenAPI type-lock |
| F1 | Auth/session shell (`/auth/me`, guest cookie, login CTA aware of OAuth gap) |
| F2 | Destination search + readiness gate (pinned sparse warn+allow; search rate limit treated as live middleware contract) |
| F3 | Compose + planner SSE progress + terminals + clarification fresh re-submit + abort-integrity proof |
| F4 | Trip detail + MapLibre GeoJSON overlay + distinct session-mismatch 403 UX |
| F5 | Trip claim + trip list (auth-required surfaces; distinct claim failure copy) |
| F6 | Day edit (reorder / add / remove / reoptimize) + invalidation |
| F7 | Hardening (error-code UX, Vitest/RTL, Playwright smoke incl. abort proxy, a11y, responsive) |

Phases MAY subdivide into numbered steps (e.g. `3.2`) matching backend step density where useful.

#### Scenario: Guest path before polished login
- **WHEN** reading F0–F4
- **THEN** guest search → readiness → generate → trip + map is achievable without requiring a polished OAuth return bounce

#### Scenario: F0 includes type-lock
- **WHEN** reading F0
- **THEN** an OpenAPI type-generation step is present before feature screens rely on wire types

### Requirement: Resilience contracts for FE external I/O
The blueprint MUST include a Resilience / UX contracts table covering at least:

| Concern | Contract elements |
|---------|-------------------|
| JSON API `fetch` | timeout/abort, credentials, typed envelope errors, toast/fallback UI |
| Planner SSE | real `AbortController` into `fetch`, abort on navigate away, pre-stream 409 handling, missing progress events on cache hit, terminal-only navigation, clarification fresh re-submit |
| Map tiles | MapTiler primary; OSM-dev only; points-only if LineString missing |
| Auth cookies | credentials always; `/auth/me` as source of guest vs user; no dual session stores |
| Rate limits | map `rate_limit_exceeded` / 429 to user-visible backoff messaging; destination-search `20/min/IP` documented as live middleware (debounce still recommended) |
| Guest-session mismatch | distinct 403 copy; no login CTA |

#### Scenario: SSE abort is specified
- **WHEN** the planner generate step is read
- **THEN** it requires AbortController wired into `fetch` on unmount/navigation, a named UI fallback on stream error/timeout, and proof criteria for server-side cancellation

#### Scenario: Search rate limit is live
- **WHEN** the destination-search step documents rate limiting
- **THEN** it treats `20/min/IP` as enforced by backend middleware (not merely soft guidance) while still recommending client debounce
