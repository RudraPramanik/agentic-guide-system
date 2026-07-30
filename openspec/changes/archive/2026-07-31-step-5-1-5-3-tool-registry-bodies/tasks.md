## 1. Step 5.1 — Schemas + registry surface

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/steps/step5.md` steps 5.1–5.3 before coding
- [x] 1.2 Extend `src/planner/tools/schemas.py`: `AgentPhase`, `PHASE_TOOLS`, `ToolResult` (+ `fallback_used`), `ToolTraceEntry`, `PendingToolCall`, `ToolContext`, twelve input models
- [x] 1.3 Extend `src/planner/tools/registry.py`: `ToolDefinition`, `TOOL_REGISTRY` with 12 stub fns (`not_implemented`), phase/precondition gating in `execute_tool`, `get_tools_for_phase`
- [x] 1.4 Run step 5.1 ✅ validation snippet (12 tools, DISCOVER schema filter, wrong-phase soft-fail, unknown_tool never raises)

## 2. Step 5.2 — DISCOVER tool bodies

- [x] 2.1 Add named constants (`RANK_EXPLANATION_TOP_N`, later `SEARCH_EXPAND_FACTOR`) in `planner/tools/constants.py` or `travel_rules` — no bare magic numbers
- [x] 2.2 Implement `check_readiness.py` (readiness via service/compute; low score → warning, still ok)
- [x] 2.3 Implement `search_places.py` (Qdrant → PostGIS fallback + `used_geo_fallback`)
- [x] 2.4 Implement `rank_places.py` (travel_engine `select_places` + `explain_selection`; no LLM)
- [x] 2.5 Wire DISCOVER fns into `TOOL_REGISTRY`; run step 5.2 ✅ validation snippet

## 3. Step 5.3 — PLAN / VALIDATE / control / REPLAN tools

- [x] 3.1 Implement `build_route` + `build_schedule` (allocate/optimize/schedule; FakeRoutingProvider-friendly)
- [x] 3.2 Implement `validate_itinerary` with locked DayPlan/TripItinerary field mapping
- [x] 3.3 Implement `finish_plan` (precondition: validate ok OR abort) + `ask_clarification`
- [x] 3.4 Implement REPLAN set: `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, `accept_partial`
- [x] 3.5 Ensure all tools return `ToolResult` only (no TravelState mutation); never raise; no LLM in tool bodies
- [x] 3.6 Run step 5.3 ✅ validation snippet (nine tools registered; finish_plan precondition_failed without validate)

## 4. Verification + context

- [x] 4.1 Run `python -m pytest tests/ -v` — P4 planner envelope + travel_engine tests still green
- [x] 4.2 Update `docs/context.md`: Progress 5.1–5.3 ✅; Implemented modules for new tool modules; Next step → 5.4; keep graph/service/HTTP as stubs
