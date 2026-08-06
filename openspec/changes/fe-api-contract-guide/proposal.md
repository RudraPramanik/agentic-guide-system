## Why

`docs/FE_guide.md` locks the Next.js stack and high-level integration rules (cookies, envelopes, route list, SSE shape), but it is not enough for a frontend team to navigate and implement against the live FastAPI contract. Request/response field shapes, per-route auth, error codes, pagination, GeoJSON properties, and SSE payloads still require reading Python schemas — and the guide itself has small inaccuracies (e.g. readiness UX mentioning `search_available`, which is not returned). We need the guide expanded into a FE-facing API navigation contract before the sibling app is scaffolded.

## What Changes

- Expand `docs/FE_guide.md` (same canonical file) with an **API contract / navigation** section set grounded in live routers + `src/*/schemas.py` — not a second competing draft.
- Add per-endpoint **auth matrix** (None / Optional / Required / ownership) aligned with `docs/context.md` Live endpoints.
- Document **TypeScript-oriented DTO sketches** for request/response bodies: auth me, destinations search/readiness, places, `PlanRequest`, trip out/edit payloads, pagination envelope.
- Document **error codes** FE should branch on (`destination_not_ready`, `not_found`, `unauthorized`, `forbidden`, `rate_limit_exceeded`, `validation_error`, SSE terminal `error` codes).
- Flesh out **SSE event catalog** (progress vs terminal) with representative `data` shapes and note OpenAPI `/docs` as the machine-readable companion.
- Document **GeoJSON FeatureCollection** property/geometry contract for MapLibre.
- Fix misleading readiness guidance (`tier` / `score` / pcts — not a returned `search_available` flag).
- Note relevant **rate limits** that affect UX (destination search, planner generate, trip edits).
- Keep non-goals: no FastAPI route changes, no FE scaffold, no OpenAPI codegen pipeline in this change.

## Capabilities

### New Capabilities

- `fe-api-contract`: Requirements for the FE-facing API navigation contract inside `docs/FE_guide.md` — endpoint auth matrix, DTO field sketches, envelopes/pagination, SSE payload catalog, GeoJSON map contract, error/rate-limit UX codes, and source-of-truth pointers (schemas + `/docs`).

### Modified Capabilities

- (none — prior `frontend-stack-guide` remains the stack/integration baseline; this change adds API-contract depth without rewriting stack locks)

## Impact

- **Docs:** `docs/FE_guide.md` expanded; may add a one-line pointer from `docs/context.md` Live endpoints → FE guide API section (optional, no progress-table churn).
- **OpenSpec:** `openspec/changes/fe-api-contract-guide/` planning artifacts.
- **Code:** none — documentation/contract only; no FastAPI or FE implementation.
- **Consumers:** Sibling Next.js team / agents building `lib/api/*` and Zod types.
- **Non-goals:** changing live endpoints; implementing OAuth `FRONTEND_URL` redirect; generating committed OpenAPI JSON; scaffolding the FE repo; evaluation HTTP (still stub).
