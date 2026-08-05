## Context

`docs/context.md` records **P6 complete** (6.0–6.5 ✅, Next → P7.1): route polylines, trips repo/service + HTTP CRUD/GeoJSON/claim, planner SSE `/generate`, Redis/InMemory rate limiter + planner `CacheBackend`, P6 pytest + `scripts/test_p6_smoke.py`. The junior developer manual index still says **Through step: P5.11** and still lists trips HTTP / planner HTTP generate as unbuilt. `system.md` still says trips “HTTP CRUD later” and planner “HTTP generate P6”; `lld.md` still says “planner cache later”.

Constraints: docs-only; tables over prose; never invent stub APIs (P7 edit/replan, evaluation HTTP remain stubs); truth source = `docs/context.md`; follow `docs/manual/06-maintenance.md` checklist.

## Goals / Non-Goals

**Goals:**
- Bring the developer manual through **P6** (expected **P6.5**) and log the phase-complete refresh.
- Catch up any residual P5.12–5.14 framing still stuck at the P5.11 marker.
- Fix concrete factual drift in `system.md` / `lld.md` (and orientation/layers if needed) found during the pass.

**Non-Goals:**
- Application code, tests, migrations, package pins.
- Rewriting `blueprint_final.md`, `AGENT.md`, or step prompts.
- Documenting unbuilt P7 trip edit/replan as if they had public APIs.
- Expanding architecture essays into phase changelogs.
- Mandatory rewrite of `p2guide.md` (only fix if a concrete post-P6 contradiction is found).

## Decisions

1. **Single catch-up refresh to P6.5 (covers missed P5.12–P6.5)**  
   - Why: Index never left P5.11; P5 and P6 both finished in context. One Through-step bump matches “phase end” cadence and avoids a second P5-only pass.  
   - Alternative: refresh only through P5.14 first — rejected; context already past P6; one sync is enough.

2. **Truth source = `docs/context.md` Implemented / Stubs / Live endpoints**  
   - Copy real-vs-stub from context: trips HTTP + GeoJSON/claim, `POST /api/v1/planner/generate` SSE, `CacheBackend` / Redis rate limiter, polylines, smoke/pytest counts.  
   - Through-step MUST NOT exceed what context marks ✅. Expected apply target: **P6.5**, Next → **P7.1**.  
   - Alternative: re-derive from OpenSpec archives — risk of documenting planned P7 APIs as shipped.

3. **Stub callouts stay precise**  
   - Real after P6: planner graph/service + SSE router, trips CRUD/GeoJSON/claim, cache backends, route polylines, `scripts/test_p6_smoke.py`.  
   - Still stub / not built: P7 trip edit/replan HTTP, evaluation HTTP, `auth/dependencies.py`; clarification-path evaluation only if context still defers it.  
   - Alternative: mark entire `trips/` as “new” without noting ownership/claim rules — rejected; juniors need ownership/guest/claim callouts from context.

4. **`system.md` / `lld.md` = opportunistic corrections only**  
   - Known drifts: `system.md` trips “HTTP CRUD later”; planner “HTTP generate P6”; Build Progress “through P5.11”. `lld.md` Cache-Aside “planner cache later”; add/ship Redis rate-limiter / Strategy backend selection if missing.  
   - Update status cells to “real / shipped” where true; do not add long “P6 complete” essays.  
   - Alternative: full system.md rewrite — rejected as churn vs architecture-essay role.

5. **Live endpoints + deployment notes in manual snapshot**  
   - Index snapshot and how-to recipes MUST mention proxy buffering off for SSE, `fetch()` (not EventSource) for POST SSE, empty `REDIS_URL` → in-memory (not shared across workers) — matching context deployment notes.  
   - Alternative: leave deployment notes only in context — rejected; juniors hitting generate will fail without the proxy/SSE note in how-to.

## Risks / Trade-offs

- [Manual over-edit] → Stick to checklist in `06-maintenance.md`; prefer row updates over new essays.  
- [Accidental P7 API invention] → Module map lists only context Implemented modules; no edit/replan routes as live.  
- [Claiming Redis as required] → Document empty `REDIS_URL` in-memory fallback as MVP default.  
- [Duplicate context.md content] → Manual stays navigational; deep truth stays in context.  
- [Missed P5.12–5.14 gaps] → Explicitly include PlannerService / tool-loop / agent smoke in module map if still marked stub in manual pages.

## Migration Plan

Docs-only session: confirm `context.md` Through-step target (P6.5 / Next P7.1) → edit `documentation.md` + `docs/manual/*` → light-touch `system.md` / `lld.md` → run `06-maintenance.md` sanity checklist vs `context.md` → no rollback beyond git revert.

## Open Questions

None — scope is documentation sync after completed P6; Through-step follows `docs/context.md` at apply time.
