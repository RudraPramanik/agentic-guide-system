## Context

`docs/context.md` records **post-P7** (7.0–7.6 ✅, production packaging, Next → operator VPS deploy via `docs/steps/blueprint_production.md`): base prefs persist, shared `populate_leg_polylines`, TripService day surgery + preserve-order schedule, trips edit HTTP (4 routes) + user-keyed `rate_limit_trip_edit`, edit/replan pytest, evaluation `mark_trip_edited` polish, P7 smoke, hosted embeddings path, deploy SOP. The junior developer manual index still says **Through step: P6.5** and still lists P7 trip edit/replan as unbuilt. `system.md` still says trips “edit/replan HTTP later (P7)” and Build Progress “through P6.5”; `lld.md` lacks shipped framing for P7 edit UoW / preserve-order / trip-edit rate limit / shared polyline helper.

Constraints: docs-only; tables over prose; never invent stub APIs (evaluation HTTP remains stub); truth source = `docs/context.md`; follow `docs/manual/06-maintenance.md` checklist; user explicitly asked to update `documentation.md`, `system.md`, and `lld.md` (manual pages are required companions of the documentation index per cadence rules).

## Goals / Non-Goals

**Goals:**
- Bring the developer manual through **P7** (expected **P7.6** / post-P7) and log the phase-complete refresh.
- Fix concrete factual drift in `system.md` / `lld.md` (and orientation/layers/wiring/recipes) found during the pass.
- Point “next” at operator VPS deploy / `blueprint_production.md`, not “build P7.1”.
- Mention production packaging / hosted embeddings at snapshot level where MiniLM-only or “edit later” framing would mislead.

**Non-Goals:**
- Application code, tests, migrations, package pins.
- Rewriting `blueprint_final.md`, `AGENT.md`, step prompts, or `FE_guide.md` wholesale.
- Documenting unbuilt evaluation HTTP as if it had public APIs.
- Expanding architecture essays into phase changelogs or implementing `docs/next_version.md` roadmap items.
- Mandatory rewrite of `p2guide.md` (only fix if a concrete post-P7 contradiction is found).

## Decisions

1. **Single catch-up refresh to P7.6 (covers full P7 + production packaging notes)**  
   - Why: Index never left P6.5; P7 phase finished in context; maintenance log already named P7 complete as the next natural refresh. One Through-step bump matches “phase end” cadence.  
   - Alternative: refresh only through 7.3 first — rejected; context already closed P7.6.

2. **Truth source = `docs/context.md` Implemented / Stubs / Live endpoints**  
   - Copy real-vs-stub from context: four trip edit routes, `rate_limit_trip_edit`, `populate_leg_polylines`, preserve-order schedule, TripEditEvent UoW + `mark_trip_edited`, `scripts/test_p7_smoke.py`, pytest ~248, hosted embeddings + deploy SOP pointers.  
   - Through-step MUST NOT exceed what context marks ✅. Expected apply target: **P7.6** (or “post-P7”), Next → **operator VPS deploy**.  
   - Alternative: re-derive from OpenSpec archives — risk of documenting planned evaluation HTTP as shipped.

3. **Stub callouts stay precise**  
   - Real after P7: prior P6 surface + trip edit/replan HTTP + shared polyline helper + evaluation flag polish + P7 smoke.  
   - Still stub / not built: evaluation HTTP, `auth/dependencies.py`; clarification-path evaluation only if context still defers it.  
   - Alternative: mark entire `evaluation/` as “done” because `mark_trip_edited` shipped — rejected; HTTP surface is still stub per context.

4. **`system.md` / `lld.md` = opportunistic corrections only (user-named targets)**  
   - Known drifts: `system.md` trips “edit/replan HTTP later (P7)”; Build Progress “through P6.5”; lifespan/embeddings language that implies MiniLM-only without hosted path. `lld.md` pattern catalog missing P7 edit UoW / preserve-order / trip-edit rate-limit dependency / public `populate_leg_polylines`.  
   - Update status cells to “real / shipped” where true; do not add long “P7 complete” essays. Link deploy SOP rather than duplicating `blueprint_production.md`.  
   - Alternative: full system.md rewrite — rejected as churn vs architecture-essay role.

5. **Manual pages are in scope even though the user named three app docs**  
   - Why: `documentation.md` is only the index; cadence rules require syncing `docs/manual/*` with the Through-step bump, or the index will contradict its own pages.  
   - Alternative: edit only the three named files — rejected; would leave `01–05` claiming “P7 next / edit unbuilt”.

6. **Live endpoints + edit rate-limit notes in how-to recipes**  
   - Index snapshot and how-to MUST list the four edit routes as live, note `require_auth` + ownership + `rate_limit_trip_edit` (user-keyed; dual OK with middleware IP), and keep prior SSE/proxy/`REDIS_URL` guidance.  
   - Alternative: leave edit routes only in context Live endpoints table — rejected; juniors following how-to would still think edits are unbuilt.

## Risks / Trade-offs

- [Manual over-edit] → Stick to checklist in `06-maintenance.md`; prefer row updates over new essays.  
- [Accidental evaluation HTTP invention] → Module map lists only context Implemented modules; no evaluation router as live.  
- [Claiming hosted embeddings as local default] → Document `PLACES_EMBEDDING_BACKEND=local` for MiniLM vs `hosted` for prod Gemini; link production blueprint for dim cutover.  
- [Duplicate context.md content] → Manual stays navigational; deep truth stays in context.  
- [Missed production packaging framing] → Snapshot one-liner + system.md layout notes pointing at `Dockerfile` / `docker-compose.prod.yml` / `blueprint_production.md` without copying the full SOP.

## Migration Plan

Docs-only session: confirm `context.md` Through-step target (P7.6 / Next operator deploy) → edit `documentation.md` + `docs/manual/*` → light-touch `system.md` / `lld.md` → run `06-maintenance.md` sanity checklist vs `context.md` → no rollback beyond git revert.

## Open Questions

None — scope is documentation sync after completed P7; Through-step follows `docs/context.md` at apply time.
