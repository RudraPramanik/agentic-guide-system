## Context

`docs/context.md` records **P4 complete** and **Next step: P5.1**. The junior developer manual index still says **Through step: P2.10** and still describes `search/` and `travel_engine/` as stubs. P2 study guide still frames next work as P3.1 and lists search/travel_engine as stubs. Critic locks for P5 are already applied into `step5.md` / blueprint / `AGENT.md` — this change does not re-touch those.

Constraints: docs-only; tables over prose; never invent stub APIs (planner LangGraph / tool bodies remain stub); truth source = `docs/context.md`.

## Goals / Non-Goals

**Goals:**
- Bring the developer manual through **P4.10** and log the deferred P3+P4 phase-complete refresh.
- Correct `p2guide.md` stub/next framing so it does not contradict post-P4 reality.
- Fix concrete factual drift in `system.md` / `lld.md` / orientation / layers found during the pass.

**Non-Goals:**
- Application code, tests, migrations, package pins.
- Rewriting `step3–5.md`, `blueprint_final.md`, `AGENT.md`, or `context.md` (already current).
- Documenting unbuilt P5 graph nodes / tool bodies as if they had public APIs.
- Expanding architecture essays into phase changelogs.

## Decisions

1. **Single catch-up refresh to P4.10 (not separate P3 then P4 manuals)**  
   - Why: Cadence missed both phase ends; one Through-step bump avoids double churn and matches “whichever comes first” intent.  
   - Alternative: two sequential refreshes — rejected; no intermediate readers need a P3-only manual snapshot.

2. **Truth source = `docs/context.md` Implemented / Stubs / Live endpoints**  
   - Copy real-vs-stub and verification artifacts from context (P3 search/enrich/index; P4 travel_engine + CORS + OsrmRoutingProvider + ToolResult envelope + p4 smoke; pytest 141).  
   - Readiness: `search_available` is live Qdrant flag (P3.6) — update any “always False” P2-era language in the manual.  
   - Alternative: re-derive from step prompts — risk of documenting planned P5 APIs as shipped.

3. **Stub callouts stay precise**  
   - Real: `src/search/*`, `src/travel_engine/*`, `src/planner/routing_provider.py`, `src/planner/tools/schemas.py`, `src/planner/tools/registry.py` (envelope stub only).  
   - Still stub: planner LangGraph / tool *bodies*, trips/evaluation except models, `auth/dependencies.py`.  
   - Alternative: mark entire `planner/` as stub — rejected; would hide the real P4 adapter/envelope already in tree.

4. **`p2guide.md` stays a P2 knowledge doc; only fix contradiction**  
   - Keep interview/engineering Q&A; update “still stubs” and “next phase” lines to match context (next = P5.1; search + travel_engine real).  
   - Alternative: rename/expand into a P4 guide — out of scope for this cadence refresh.

5. **`system.md` / `lld.md` = opportunistic corrections only**  
   - Scan for wrong “stub / not built / next phase” claims; do not add long “P3/P4 complete” sections.  
   - Alternative: full system.md rewrite — rejected as churn vs architecture-essay role.

6. **Do not bump `context.md` except for a link/path typo**  
   - Context already records P4 complete; this change is the deferred manual refresh it points agents at.

## Risks / Trade-offs

- [Manual over-edit] → Stick to checklist in `06-maintenance.md`; prefer row updates over new essays.  
- [Accidental P5 API invention] → Module map lists only context “Implemented modules”; planner tool bodies remain stub callouts.  
- [p2guide becomes a second context.md] → Limit edits to phase framing / stubs / next; leave P2 teaching body intact.  
- [Readiness language regresses] → Preserve P2 formula-true floors; additionally note live `search_available` from Qdrant.

## Migration Plan

Docs-only session: edit files → run `06-maintenance.md` sanity checklist vs `context.md` → no rollback beyond git revert.

## Open Questions

None — scope is documentation sync after completed P3+P4 phases, before P5 implementation.
