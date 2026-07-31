## ADDED Requirements

### Requirement: Manual refresh after P5 phase completion

After P5 is recorded complete in `docs/context.md` (Progress 5.1–5.14 ✅, next step P6.1), the developer manual MUST be refreshed in the same docs-sync change (or immediately after). The index `docs/app/documentation.md` MUST set **Through step** to at least **P5.14**, bump **Last refreshed**, and update the snapshot so it no longer claims planner LangGraph nodes, tool bodies, orchestration, compiled graph, evaluation generation persist, `PlannerService` SSE bridge, `tests/planner/test_tool_loop.py`, or `scripts/test_agent.py` are unbuilt (when those rows are ✅ in context). The maintenance refresh log MUST record a phase-complete (or deferred catch-up) row covering through P5.14. If context has not yet marked 5.12–5.14 ✅, Through step MUST NOT exceed the highest validated P5 step in context.

#### Scenario: Index reflects P5 complete

- **WHEN** a developer opens `docs/app/documentation.md` after this refresh with context showing P5.14 done
- **THEN** the header shows Through step ≥ P5.14 and the snapshot lists P5 planner graph/tools/service bridge + verification artifacts as present, with next product work described as P6.1 (not “build P5”)

#### Scenario: Maintenance log records the catch-up

- **WHEN** the refresh is finished for P5.14
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P5.14 (or equivalent) with trigger noting P5 phase complete (or P5 catch-up)

#### Scenario: Through-step does not overshoot context

- **WHEN** `docs/context.md` still lists Next as P5.12 (or any incomplete P5 step)
- **THEN** the manual Through step stays ≤ the highest ✅ P5 step and does not claim unfinished service/smoke modules as shipped

### Requirement: Module map and wiring include P5 planner artifacts

The module map and imports/wiring pages MUST list as real (not stub) whatever `docs/context.md` marks implemented for P5, including at minimum when ✅: `AgentPhase` / `PHASE_TOOLS` / 12-tool registry + phase-gated `execute_tool`, tool bodies, `apply_tool_result` / `maybe_transition_phase` / stuck-detector orchestration, `TravelState`, `build_agent_messages`, graph nodes (`parse_preferences`, `agent`, `tool_executor`, `write_narrative`, `record_evaluation`), `build_planner_graph` / `get_compiled_graph`, evaluation repository/service for generation persist, and (when ✅) `PlannerService.generate` SSE bridge, `tests/planner/test_tool_loop.py`, `scripts/test_agent.py`. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (trips CRUD HTTP, planner HTTP `/planner/generate`, `auth/dependencies.py`, and any deferred clarification-path evaluation note).

#### Scenario: Junior looks up planner graph

- **WHEN** a developer opens the module map looking for `planner/graph/`
- **THEN** they see state, messages, nodes, and builder marked as real (when context says so), not as “stubs (later)”

#### Scenario: Junior looks up PlannerService

- **WHEN** a developer opens the module map looking for `planner/service.py` after context marks 5.12 ✅
- **THEN** they see the SSE bridge / `generate` path as real, and FastAPI `/planner/generate` still called out as not registered (P6)

### Requirement: How-to-change recipes cover P5 verification paths

Recipes MUST mention running `python scripts/test_agent.py` (when context marks 5.14 ✅) and `python -m pytest tests/planner` (including tool-loop tests) where appropriate. Recipes MUST NOT tell juniors to call `POST /api/v1/planner/generate` as a live endpoint until context lists it under Live endpoints.

#### Scenario: Smoke recipe after P5

- **WHEN** a developer follows verification recipes after the P5 refresh
- **THEN** they are directed to the agent smoke script and planner pytest packages consistent with `docs/context.md`, not only P4 smoke

#### Scenario: No invented planner HTTP

- **WHEN** a developer reads how-to-change or live-endpoint guidance after P5
- **THEN** they do not find `/api/v1/planner/generate` presented as a registered live route

### Requirement: Architecture docs light-touch after P5

`docs/app/system.md` and `docs/app/lld.md` MUST NOT retain factual claims that contradict post-P5 `docs/context.md` (e.g. “planner LangGraph / tool bodies still in P5”, pattern catalog cells still implying phase-gated tool loop is unbuilt). Corrections MUST be minimal status/framing fixes — not architecture rewrites. Residual stubs (trips HTTP, planner HTTP) MAY remain called out as future work.

#### Scenario: system.md planner row matches reality

- **WHEN** a reader checks the `src/planner/` summary in `system.md` after P5 is complete in context
- **THEN** the row no longer claims LangGraph / tool bodies are only future P5 work; SSE HTTP may still be noted as P6

#### Scenario: lld.md pattern table marks shipped P5 patterns

- **WHEN** a reader checks the pattern catalog in `lld.md` for Tool Registry / Phase-Gated Tool Loop / Bookend Nodes after P5 complete
- **THEN** those rows are framed as shipped (or present), not as upcoming P5-only work

## MODIFIED Requirements

### Requirement: Module map with real vs stub

The manual MUST include a module/package map keyed to the repository layout, listing key files and responsibilities for implemented modules through the current “through step” marker, and MUST mark stub-only packages so juniors do not assume public APIs exist. After the P5 catch-up refresh, the through-step marker MUST be at least P5.14 when context records P5 complete, and MUST treat geo gateways, destinations/places HTTP, readiness (including live `search_available`), P3 search/enrich/index, CORS, full `travel_engine/*`, planner routing provider, full P5 tools + orchestration + graph nodes/builder + evaluation generation persist + (when ✅) PlannerService SSE bridge and P5 verification artifacts as real. Stub callouts MUST match `docs/context.md` (trips CRUD HTTP; planner HTTP generate; `auth/dependencies.py`; any still-deferred clarification evaluation).

#### Scenario: Stub packages are explicit

- **WHEN** a developer looks up trips HTTP or `POST /planner/generate` while those remain unbuilt
- **THEN** the manual states they are not implemented / not registered without inventing public APIs

#### Scenario: Real geo modules are listed

- **WHEN** the “through step” is at least P2.2
- **THEN** `src/geo/geocoder.py` and `src/geo/overpass.py` appear as real gateways with their public entry points (`geocode`, `fetch_pois`)

#### Scenario: P2 verification modules are listed as real

- **WHEN** the “through step” is at least P2.10
- **THEN** `src/geo/osrm.py`, destinations/places routers and readiness, P2 pytest packages, and `scripts/test_p2_smoke.py` appear as real

#### Scenario: P3 and P4 modules are listed as real

- **WHEN** the “through step” is at least P4.10
- **THEN** `src/search/*`, enrich/index scripts, `src/travel_engine/*`, `OsrmRoutingProvider`, and `scripts/test_p4_smoke.py` appear as real

#### Scenario: P5 planner modules are listed as real

- **WHEN** the “through step” is at least P5.14 (and context marks those steps ✅)
- **THEN** planner tools/orchestration/graph nodes/builder, evaluation generation persist, PlannerService bridge, tool-loop tests, and `scripts/test_agent.py` appear as real
