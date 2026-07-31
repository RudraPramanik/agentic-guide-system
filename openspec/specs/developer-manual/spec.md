## Purpose

Junior-oriented developer manual (`docs/app/documentation.md` → `docs/manual/`) covering layers, module map, wiring, change recipes, and refresh cadence.

## Requirements

### Requirement: Developer manual entry index
The project SHALL provide a junior-oriented developer manual whose entry point is `docs/app/documentation.md`. The index MUST state purpose (developer orientation, not traveler product docs), last-refreshed date, “through step” marker, recommended read order, and a table of contents linking to pages under `docs/manual/`.

#### Scenario: Junior opens the index
- **WHEN** a developer opens `docs/app/documentation.md`
- **THEN** they see what the manual is for, how far it covers (step id), and links to orientation, layers, module map, imports/wiring, how-to-change, and maintenance pages

### Requirement: Layer and AI boundary explanation
The manual MUST explain the backend layering (Router → Service → Repository; `geo/` gateways; `core/llm` as sole LLM entry; deterministic vs LLM responsibilities) and why those boundaries exist, linking to `AGENT.md` for hard rules without copying them wholesale.

#### Scenario: Junior asks where LLM calls go
- **WHEN** a developer reads the layers page looking for AI/LLM usage
- **THEN** they learn that LLM calls go only through `src/core/llm/client.py` and that place IDs / coordinates / times must not come from free-form LLM output

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

### Requirement: Manual refresh after P2 phase completion
After P2.9 and P2.10 are recorded complete in `docs/context.md`, the developer manual MUST be refreshed in the same docs-sync change (or immediately after). The index `docs/app/documentation.md` MUST set **Through step** to at least **P2.10**, bump **Last refreshed**, and update the snapshot so it no longer claims P2 pytest or `scripts/test_p2_smoke.py` are unbuilt. The maintenance refresh log MUST record a phase-complete row for P2.

#### Scenario: Index reflects P2 complete
- **WHEN** a developer opens `docs/app/documentation.md` after this refresh
- **THEN** the header shows Through step ≥ P2.10 and the snapshot lists P2 pytest packages and the P2 smoke script as present, with next product work described as P3+ (not “build 2.9/2.10”)

#### Scenario: Maintenance log records the phase end
- **WHEN** the refresh is finished
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P2.10 (or equivalent) with trigger “P2 phase complete”

### Requirement: Manual refresh after P3 and P4 phase completion

After P3 and P4 are recorded complete in `docs/context.md` (next step P5.1), the developer manual MUST be refreshed before P5 implementation begins (or in the same docs-sync change that closes the gap). The index `docs/app/documentation.md` MUST set **Through step** to at least **P4.10**, bump **Last refreshed**, and update the snapshot so it no longer claims `search/`, `travel_engine/`, P3 enrich/index, CORS, `OsrmRoutingProvider`, or `scripts/test_p4_smoke.py` are unbuilt. The maintenance refresh log MUST record a phase-complete (or deferred catch-up) row covering through P4.10.

#### Scenario: Index reflects P4 complete

- **WHEN** a developer opens `docs/app/documentation.md` after this refresh
- **THEN** the header shows Through step ≥ P4.10 and the snapshot lists P3 search/enrich/index and P4 travel_engine + verification artifacts as present, with next product work described as P5.1 (not “build P3/P4”)

#### Scenario: Maintenance log records the catch-up

- **WHEN** the refresh is finished
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P4.10 (or equivalent) with trigger noting P3+P4 phase catch-up (or P4 phase complete)

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

### Requirement: Module map and wiring include P2 verification artifacts
The module map and imports/wiring pages MUST list as real (not stub): `tests/geo/`, `tests/destinations/`, `tests/places/`, `tests/scripts/`, `scripts/test_p2_smoke.py`, and the seed pipeline helper `seed_destination_into` alongside existing `seed_places` / `seed_destination`. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (planner, search, travel_engine, trips/evaluation except models, `auth/dependencies.py`).

#### Scenario: Junior looks up P2 tests
- **WHEN** a developer opens the module map looking for P2 tests
- **THEN** they see the geo/destinations/places/scripts test packages and the P2 smoke script marked as real, not “lands in 2.9–2.10”

### Requirement: Module map and wiring include P3 and P4 artifacts

The module map and imports/wiring pages MUST list as real (not stub): `src/search/*` (client, embeddings, places_index), place enrich path + `enriched_tags`, `scripts/enrich_places.py` / `scripts/index_places.py`, CORS middleware + `CORS_ALLOWED_ORIGINS`, all `src/travel_engine/*` modules through `trip_validator`, `src/planner/routing_provider.py`, `src/planner/tools/schemas.py` (`ToolResult`), `src/planner/tools/registry.py` (`execute_tool` envelope), `tests/travel_engine/` / `tests/planner/` / `tests/search/` as applicable, and `scripts/test_p4_smoke.py`. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (planner LangGraph / tool bodies, trips/evaluation except models, `auth/dependencies.py`).

#### Scenario: Junior looks up travel_engine

- **WHEN** a developer opens the module map looking for `travel_engine/`
- **THEN** they see the P4 pure-Python modules marked as real with no I/O claim, not as “stubs (later)”

#### Scenario: Junior looks up planner package

- **WHEN** a developer opens the module map looking for `planner/`
- **THEN** they see routing provider + tools envelope as real, and LangGraph / tool bodies explicitly stubbed pending P5

### Requirement: Module map and wiring include P5 planner artifacts

The module map and imports/wiring pages MUST list as real (not stub) whatever `docs/context.md` marks implemented for P5, including at minimum when ✅: `AgentPhase` / `PHASE_TOOLS` / 12-tool registry + phase-gated `execute_tool`, tool bodies, `apply_tool_result` / `maybe_transition_phase` / stuck-detector orchestration, `TravelState`, `build_agent_messages`, graph nodes (`parse_preferences`, `agent`, `tool_executor`, `write_narrative`, `record_evaluation`), `build_planner_graph` / `get_compiled_graph`, evaluation repository/service for generation persist, and (when ✅) `PlannerService.generate` SSE bridge, `tests/planner/test_tool_loop.py`, `scripts/test_agent.py`. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (trips CRUD HTTP, planner HTTP `/planner/generate`, `auth/dependencies.py`, and any deferred clarification-path evaluation note).

#### Scenario: Junior looks up planner graph

- **WHEN** a developer opens the module map looking for `planner/graph/`
- **THEN** they see state, messages, nodes, and builder marked as real (when context says so), not as “stubs (later)”

#### Scenario: Junior looks up PlannerService

- **WHEN** a developer opens the module map looking for `planner/service.py` after context marks 5.12 ✅
- **THEN** they see the SSE bridge / `generate` path as real, and FastAPI `/planner/generate` still called out as not registered (P6)

### Requirement: How-to-change recipes stay formula-true on readiness
Recipes that mention destination readiness after seed MUST distinguish Overpass/seed volume (`place_count >= 50`) from unenriched limited-band scoring (`place_count >= 100` preferred; `>= 88` minimum for score ≥ 0.35). They MUST NOT imply that `place_count >= 50` alone yields `tier=limited`.

#### Scenario: Seed recipe mentions readiness band
- **WHEN** a developer follows the seed / readiness recipe
- **THEN** they are told volume ≥50 is not sufficient for limited-band claims and to use a larger radius (e.g. `--radius 50`) when they need ~100+ places for `tier=limited`

### Requirement: How-to-change recipes cover P3/P4 verification paths

Recipes MUST mention running `python scripts/test_p4_smoke.py` and `python -m pytest tests/` (including travel_engine / planner / search packages) where appropriate. Readiness recipes MUST note that `search_available` reflects live Qdrant availability (`is_qdrant_available`) after P3.6, while preserving the existing formula-true place_count floors for sparse vs limited-band scoring.

#### Scenario: Smoke recipe after P4

- **WHEN** a developer follows verification recipes after the refresh
- **THEN** they are directed to the P4 smoke script and pytest packages consistent with `docs/context.md`, not only P2 smoke

#### Scenario: Readiness search_available is live

- **WHEN** a developer reads readiness language in the manual
- **THEN** they learn `search_available` is the live Qdrant flag, not permanently False as in the P2-era snapshot

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

### Requirement: Import and wiring map
The manual MUST document primary import/call relationships among implemented packages (e.g. `main` → routers/middleware; auth router → service → repository; geo modules → `get_settings` + schemas), using tables and/or diagrams so a junior can see which file connects to which.

#### Scenario: Auth wiring is traceable
- **WHEN** a developer wants to follow a `/api/v1/auth/*` request
- **THEN** the manual points them from `src/auth/router.py` → `AuthService` → `UserRepository` → DB session dependency

### Requirement: How-to-change recipes
The manual MUST include practical “I want to…” recipes for common changes (add an env setting, add a domain endpoint following Router→Service→Repository, call external geo APIs, add an Alembic migration, run validation scripts/tests), each naming the first files to open.

#### Scenario: Adding a setting
- **WHEN** a developer needs a new configuration value
- **THEN** the recipe directs them to `src/config.py` + `.env.example` and forbids direct `os.environ.get()` in feature code

### Requirement: Update cadence and maintenance hooks
The developer manual MUST be refreshed when a full build phase completes **or** after every 4–5 validated steps since the index “through step” marker, whichever comes first. `docs/context.md` MUST link to the manual. Project Cursor rules MUST mention this cadence so agents do not rewrite the manual on every single step. Each validated step still updates `docs/context.md` as today.

#### Scenario: Cadence after five steps
- **WHEN** five validated steps land since the manual’s last “through step” and no full phase boundary occurred
- **THEN** the completing agent (or developer) updates the manual pages and bumps the index “Last refreshed” / “through step” fields

#### Scenario: Context still updated every step
- **WHEN** any single build step is validated
- **THEN** `docs/context.md` is updated even if the developer manual is not refreshed that step
