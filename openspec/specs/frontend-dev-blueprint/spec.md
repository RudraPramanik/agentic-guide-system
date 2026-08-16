## Purpose

Frontend development source-of-truth rules: `docs/blueprint_frontend.md` is the phased FE build bible; `docs/FE_guide.md` remains the stack + live API wire contract.

## Requirements

### Requirement: Frontend blueprint is the FE development source of truth
The project SHALL provide `docs/blueprint_frontend.md` as the single source of truth for **frontend development** of the sibling Next.js app (phased build, principles, AGENT guardrails, resilience/UX failure contracts, package order).

`docs/FE_guide.md` MUST remain the canonical stack + live API integration contract. The frontend blueprint MUST consume that contract and MUST NOT redefine endpoint paths, auth matrix, envelopes, SSE event names, or DTO field names in conflict with `FE_guide.md` / Python schemas.

#### Scenario: Agent knows which doc to open
- **WHEN** an implementer starts a frontend build session
- **THEN** they use `docs/blueprint_frontend.md` for phased steps and guardrails, and `docs/FE_guide.md` for stack/API wire contracts

#### Scenario: Contract conflict resolution
- **WHEN** blueprint text disagrees with Python schemas or `FE_guide.md` on a public route/DTO
- **THEN** schemas / `FE_guide.md` win, and the blueprint MUST be updated in the same change window

### Requirement: Blueprint mirrors backend rigor structure
`docs/blueprint_frontend.md` MUST include at least these top-level sections (titles may vary slightly, content MUST cover each concern):

1. Principles (numbered table)
2. FE `AGENT.md` guardrails (copy-ready block for the sibling FE repo root)
3. Project / repo structure (feature-first layout aligned with `FE_guide.md`)
4. Environment variables (FE-only vs backend-must-match)
5. Deployment / cookie decisions (Option A pointer; no competing SameSite model)
6. Resilience / UX failure contracts (timeouts, retries where appropriate, named fallbacks)
7. Domain client + SSE + map design blocks
8. Phase Blueprint (F0–Fn) with per-step pattern, failure boundary, and proof
9. Failure Boundary Summary table
10. Package Install Order
11. Deferred / known gaps (OAuth return, narrative durability, evaluation HTTP)

#### Scenario: Structure parity with backend bible
- **WHEN** a reader compares `blueprint_frontend.md` to `blueprint_final.md`
- **THEN** they find the same class of rigor (principles, AGENT rules, resilience, phases with proofs, failure summary) adapted to FE concerns

### Requirement: No happy-path-only steps
Every phase step in the frontend blueprint MUST name:

- an LLD / FE pattern (🏗️)
- a failure boundary or named fallback (🚨)
- a concrete proof / verification command or checklist (✅)

Steps MUST design for network failure, envelope errors, rate limits, SSE abort, empty readiness, ownership 403, and map tile/GeoJSON degradation — not only the successful search→generate→trip path.

#### Scenario: Step has failure + proof
- **WHEN** any F-step subsection is read
- **THEN** it includes an explicit failure/fallback note and a verification criterion

### Requirement: FE AGENT guardrails are separate from backend AGENT.md
The frontend blueprint MUST provide a complete FE `AGENT.md` content block for the sibling Next.js repo. Backend root `AGENT.md` MUST NOT be rewritten to include FE rules.

FE hard rules MUST include at least:

- API access only via shared `lib/api` client (`credentials: "include"`)
- No tokens in `localStorage` / readable cookies
- Planner streaming only via POST `fetch` + ReadableStream (never `EventSource`)
- Server state via TanStack Query; Zustand only for ephemeral UI
- Types/DTOs must follow `FE_guide.md` / OpenAPI; do not invent endpoints
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
| F0 | Scaffold, AGENT.md, env, shared API client + envelopes, providers |
| F1 | Auth/session shell (`/auth/me`, guest cookie, login CTA aware of OAuth gap) |
| F2 | Destination search + readiness gate |
| F3 | Compose + planner SSE progress + terminal handling |
| F4 | Trip detail + MapLibre GeoJSON overlay |
| F5 | Trip claim + trip list (auth-required surfaces) |
| F6 | Day edit (reorder / add / remove / reoptimize) + invalidation |
| F7 | Hardening (error-code UX, rate-limit UX, Vitest/RTL, Playwright smoke) |

Phases MAY subdivide into numbered steps (e.g. `3.2`) matching backend step density where useful.

#### Scenario: Guest path before polished login
- **WHEN** reading F0–F4
- **THEN** guest search → readiness → generate → trip + map is achievable without requiring a polished OAuth return bounce

### Requirement: Explicit MVP rules for known product gaps
The blueprint MUST document these locked MVP behaviors:

1. **Day narrative:** `TripOut` does not persist day title/narrative. MVP FE MUST either (a) render narrative from the terminal `itinerary_done` payload for the active session and accept loss on hard reload, or (b) ship trip UI without prose until a backend persistence follow-up. The chosen option MUST be stated; inventing a narrative API is forbidden.
2. **OAuth return:** Login UX remains incomplete until API `FRONTEND_URL` redirect. MVP MUST not block guest generate/trip/map on polished login.
3. **Evaluation HTTP:** Still stub — FE MUST NOT invent evaluation screens or clients.

#### Scenario: Narrative rule is unambiguous
- **WHEN** an FE agent implements the trip screen
- **THEN** the blueprint states whether narrative comes from SSE session cache or is deferred — not both ambiguously

### Requirement: Resilience contracts for FE external I/O
The blueprint MUST include a Resilience / UX contracts table covering at least:

| Concern | Contract elements |
|---------|-------------------|
| JSON API `fetch` | timeout/abort, credentials, typed envelope errors, toast/fallback UI |
| Planner SSE | abort on navigate away, pre-stream 409 handling, missing progress events on cache hit, terminal-only navigation |
| Map tiles | MapTiler primary; OSM-dev only; points-only if LineString missing |
| Auth cookies | credentials always; `/auth/me` as source of guest vs user; no dual session stores |
| Rate limits | map `rate_limit_exceeded` / 429 to user-visible backoff messaging |

#### Scenario: SSE abort is specified
- **WHEN** the planner generate step is read
- **THEN** it requires AbortController (or equivalent) on unmount/navigation and a named UI fallback on stream error/timeout

### Requirement: Context pointer without progress churn
After the blueprint lands, `docs/context.md` MUST gain a short pointer to `docs/blueprint_frontend.md` under deployment/frontend notes (or equivalent). Progress/phase tables MUST NOT be rewritten as if FE phases were backend steps.

#### Scenario: Context points to FE bible
- **WHEN** an agent reads `docs/context.md` frontend notes
- **THEN** they see a link to both `FE_guide.md` (contract) and `blueprint_frontend.md` (phased build)

### Requirement: FE_guide documents on-demand prepare and guest generate

`docs/FE_guide.md` MUST document `POST /api/v1/destinations/{destination_id}/prepare` (auth None, `ApiResponse` prepare DTO, HTTP 200 `ready` vs 202 `preparing`) in the destinations auth matrix and Live-style endpoint table. The MVP screen flow MUST be: search any place → readiness (may be sparse / `place_count=0`) → **prepare** → poll `GET /destinations/{id}/readiness` until `place_count` meets the planner floor or a client timeout → compose → guest generate. The guide MUST state that generate remains optional auth (no Google login), that 409 `destination_not_ready` means the place floor is unmet (call prepare / wait, do not treat as a stream or login failure), and that guests still open trips via `trip_id` + `wandr_session` (not `GET /trips` list). The guide MUST state that search does not scrape Overpass and that country/region ingest is out of scope. Default JSON client timeout guidance MUST warn that prepare is 202 (do not block 90s on search; poll readiness; do not treat the first sparse poll as failure).

#### Scenario: Frontend author can wire prepare without reading Python

- **WHEN** a frontend developer opens `docs/FE_guide.md` after this change
- **THEN** they find prepare method/path/auth, 200 vs 202, the prepare DTO field names, poll-readiness steps, and 409 vs login guidance in that file

#### Scenario: Guest generate stays no-login in the guide

- **WHEN** the guide describes generate after a newly prepared place
- **THEN** it MUST NOT require Google login or `wandr_token` to search, prepare, generate, or `GET /trips/{id}` for the session that generated the trip

#### Scenario: Empty readiness is not a frontend bug

- **WHEN** search returns a destination with `place_count=0` / score 0
- **THEN** the guide MUST instruct the FE to offer prepare (or equivalent) rather than treating 409 as an auth or SSE client defect
