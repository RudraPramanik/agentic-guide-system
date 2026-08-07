## 1. Scaffold the FE bible

- [x] 1.1 Create `docs/blueprint_frontend.md` with title, role statement (FE development SSOT), supersedes-none note, and relationship table: `FE_guide.md` (contract) vs this file (phased build) vs `blueprint_final.md` (backend)
- [x] 1.2 Add conflict rule: schemas → OpenAPI → `FE_guide.md` → this blueprint
- [x] 1.3 Add “What’s in this version” table summarizing locked decisions from design.md (F0–F7, narrative Option A, guest-first, separate FE AGENT)

## 2. Principles + FE AGENT.md

- [x] 2.1 Write numbered Principles table (13 intents from design D3 — packages at point of use, failure boundary per step, trip-as-artifact, cookie client, Query vs Zustand, abortable streams, envelope discipline, degrade map not blank trip, etc.)
- [x] 2.2 Embed copy-ready FE `AGENT.md` hard rules block (architecture, resilience/UX, streaming, conventions, when-in-doubt) — sibling FE repo only; do not edit backend `AGENT.md`
- [x] 2.3 Explicitly state backend `AGENT.md` remains API-only

## 3. Structure, env, deployment pointers

- [x] 3.1 Document sibling FE repo feature-first tree aligned with `FE_guide.md` §12 (`app/`, `features/`, `lib/api`, `lib/sse`, `store/`, `providers/`)
- [x] 3.2 Document FE env vars only (`NEXT_PUBLIC_API_URL`, map style URL) and backend-must-match checklist (CORS, OAuth, Option A domain) by reference to `FE_guide.md` §4–5
- [x] 3.3 Lock deployment/cookie note: Option A SameSite Lax; no competing cookie model; OAuth return gap deferred

## 4. Resilience, design blocks, failure summary

- [x] 4.1 Write Resilience / UX Contracts table (JSON fetch, SSE, map tiles, GeoJSON, `/auth/me`, rate-limit UX) per design D5
- [x] 4.2 Write short design blocks: API Gateway client + envelope adapters; Abortable planner SSE; MapLibre + GeoJSON degrade rules; Query key/invalidation rules for trips/edits/claim
- [x] 4.3 Write LLD / FE Pattern Reference catalog (Gateway, Envelope Adapter, Abortable Stream, Null/Empty UI, Cookie session probe, Thin UI store, Feature folders)
- [x] 4.4 Write Failure Boundary Summary table covering network/CORS, envelope codes (`destination_not_ready`, 401/403/404/422/429/5xx), SSE terminals/timeout/cache-hit missing tools, map tile fail, missing polylines, OAuth incomplete, evaluation HTTP stub

## 5. Phase Blueprint F0–F7

- [x] 5.0 Add Phase Blueprint legend (📦 🏗️ 🚨 ☁️ 🔒 ✅) and rule: no happy-path-only steps
- [x] 5.1 Author **F0 — Scaffold & core client** steps: repo skeleton, FE AGENT.md, env example, `lib/api/client.ts` envelopes, Query/theme/toaster providers, package installs at point of use — each with pattern + failure + proof
- [x] 5.2 Author **F1 — Session shell**: `/auth/me`, guest vs user UI, login CTA that documents OAuth gap, logout clears token awareness
- [x] 5.3 Author **F2 — Destinations**: search (min q=2, 429 UX), readiness gate by `tier`/message (no `search_available` field), sparse/limited/ready branching
- [x] 5.4 Author **F3 — Generate**: compose `PlanRequest`, POST SSE parser, progress UI, pre-stream 409, terminals (`itinerary_done` → navigate by `trip_id`; `error`; `clarification_needed`), AbortController, cache-hit without tool events, narrative Option A session capture
- [x] 5.5 Author **F4 — Trip + map**: `GET /trips/{id}`, MapLibre + `GET .../geojson`, points-only fallback, list-first if tiles fail
- [x] 5.6 Author **F5 — Claim & trip list**: `GET /trips`, claim with session match, auth-required delete — OAuth incomplete UX called out
- [x] 5.7 Author **F6 — Day edit**: reorder/add/remove/reoptimize mutations, Query invalidation, 403/409/422/429 handling
- [x] 5.8 Author **F7 — Hardening**: error-code toast map from `FE_guide.md` §16, Vitest/RTL for client/SSE parser, Playwright smoke, deferred observability

## 6. Package order, deferred, timeline

- [x] 6.1 Write Package Install Order table mapped to F-steps (Next/TS/Tailwind/shadcn first; Query; MapLibre; RHF+Zod; Motion; Vitest/Playwright later — no packages before need)
- [x] 6.2 Write Deferred / known gaps: `FRONTEND_URL` OAuth bounce; narrative persistence on trip; evaluation HTTP; Next BFF; Google Maps; AI SDK chat surface
- [x] 6.3 Optional Timeline Summary (days per F-phase) — rough, non-binding
- [x] 6.4 Quick reference: what FE MUST / MUST NOT do (mirror backend “LLM can/cannot” style for FE)

## 7. Cross-links + validate

- [x] 7.1 Add short pointer in `docs/context.md` deployment/frontend notes to `blueprint_frontend.md` (keep `FE_guide.md` pointer; no Progress-table churn). Optionally fix stale readiness `search_available` wording in Live endpoints if touching that paragraph
- [x] 7.2 Add one-line cross-link at top of `docs/FE_guide.md` → phased build bible
- [x] 7.3 Validate: no invented routes/DTOs vs `FE_guide.md` Live matrix; narrative + OAuth rules unambiguous; every F-step has 🚨 + ✅; backend `AGENT.md` untouched
- [x] 7.4 Confirm non-goals held: no Next.js scaffold in this repo, no FastAPI code changes in this change
