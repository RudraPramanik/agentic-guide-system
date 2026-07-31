## Context

`docs/context.md` records P5.1–5.11 done (Next = P5.12 at last agent checkpoint). Sibling change `step-5-12-5-14-planner-service-tests-smoke` has implemented service/SSE bridge + tool-loop tests + smoke script; remaining work is smoke proof + context bump to P5.14 / Next P6.1. The junior developer manual index still says **Through step: P4.10** and still describes planner LangGraph / tool bodies as stubs. `p2guide.md`, `system.md`, and `lld.md` still frame “next = P5” / planner incomplete in places.

Constraints: docs-only; tables over prose; never invent stub APIs (trips HTTP, planner HTTP `/planner/generate` remain P6); truth source = `docs/context.md`; follow `docs/manual/06-maintenance.md` checklist.

## Goals / Non-Goals

**Goals:**
- Bring the developer manual through **P5** (expected **P5.14**) and log the phase-complete refresh.
- Sync `context.md` Through-step target if still lagging after sibling validation (Progress / Implemented / Stubs / Next → P6.1).
- Correct `p2guide.md` stub/next framing so it does not contradict post-P5 reality.
- Fix concrete factual drift in `system.md` / `lld.md` / orientation / layers found during the pass.

**Non-Goals:**
- Application code, tests, migrations, package pins.
- Rewriting `step5.md`, `blueprint_final.md`, or `AGENT.md`.
- Documenting unbuilt P6 HTTP generate / trips CRUD as if they had public APIs.
- Expanding architecture essays into phase changelogs.
- Running or fixing the agent smoke script beyond what is required to know what `context.md` may claim (prefer sibling change for that).

## Decisions

1. **Single catch-up refresh to P5.14 (not per-step manual bumps)**  
   - Why: Cadence missed ~11+ P5 steps since P4.10; one Through-step bump matches “phase end or 4–5 steps” and avoids churn.  
   - Alternative: refresh only through P5.11 now, then again after 5.14 — rejected; prefer apply after sibling closeout so one refresh covers full P5.

2. **Truth source = `docs/context.md` Implemented / Stubs / Live endpoints**  
   - Copy real-vs-stub and verification artifacts from context (tools + orchestration + graph nodes/builder + evaluation persist + PlannerService bridge + tool-loop tests + `scripts/test_agent.py` when marked done).  
   - Through-step MUST NOT exceed what context marks ✅. Expected apply target: P5.14, Next → P6.1.  
   - Alternative: re-derive from step prompts — risk of documenting planned P6 APIs as shipped.

3. **Ordering with sibling change**  
   - Prefer completing `step-5-12-5-14` tasks 4.2–4.3 first (smoke + context). If applying while context still says Next P5.12, either (a) finish context bump here only for modules already validated in context, or (b) Through-step stays ≤ highest ✅ step (P5.11) — do not claim service/smoke shipped.  
   - Alternative: block this change until sibling archives — acceptable but not required if context is already current.

4. **Stub callouts stay precise**  
   - Real after P5: `planner/tools/*` (12 bodies + registry/orchestration), `planner/graph/*` (state, messages, nodes, builder), `evaluation` repo/service (generation persist), `PlannerService.generate` SSE bridge (no FastAPI router yet).  
   - Still stub / not built: trips CRUD HTTP, `POST /api/v1/planner/generate` (P6), `auth/dependencies.py`; clarification-path evaluation only if context still defers it.  
   - Alternative: mark entire `planner/` as stub — rejected; would hide shipped P5 graph.

5. **`p2guide.md` stays a P2 knowledge doc; only fix contradiction**  
   - Keep interview/engineering Q&A; update “still stubs” and “next phase” lines to match context (next = P6.1; planner graph/tools real).  
   - Alternative: rename/expand into a P5 guide — out of scope.

6. **`system.md` / `lld.md` = opportunistic corrections only**  
   - Scan for wrong “stub / not built / next phase” claims (e.g. planner “LangGraph in P5”, pattern table still “P5” as future). Update status cells to “real / shipped” where true; do not add long “P5 complete” essays.  
   - Alternative: full system.md rewrite — rejected as churn vs architecture-essay role.

## Risks / Trade-offs

- [Manual over-edit] → Stick to checklist in `06-maintenance.md`; prefer row updates over new essays.  
- [Accidental P6 API invention] → Module map lists only context “Implemented modules”; no `/planner/generate` as live.  
- [Claiming 5.12–5.14 before smoke] → Through-step gated on `context.md` ✅ rows only.  
- [p2guide becomes a second context.md] → Limit edits to phase framing / stubs / next; leave P2 teaching body intact.  
- [Duplicate work with sibling 4.3] → If sibling already updated context, this change only refreshes the manual + architecture light touch.

## Migration Plan

Docs-only session: confirm `context.md` Through-step target → edit manual / p2guide / system / lld → run `06-maintenance.md` sanity checklist vs `context.md` → no rollback beyond git revert.

## Open Questions

None — scope is documentation sync after completed (or nearly completed) P5; Through-step follows `context.md` at apply time.
