## ADDED Requirements

### Requirement: Manual refresh after P3 and P4 phase completion

After P3 and P4 are recorded complete in `docs/context.md` (next step P5.1), the developer manual MUST be refreshed before P5 implementation begins (or in the same docs-sync change that closes the gap). The index `docs/app/documentation.md` MUST set **Through step** to at least **P4.10**, bump **Last refreshed**, and update the snapshot so it no longer claims `search/`, `travel_engine/`, P3 enrich/index, CORS, `OsrmRoutingProvider`, or `scripts/test_p4_smoke.py` are unbuilt. The maintenance refresh log MUST record a phase-complete (or deferred catch-up) row covering through P4.10.

#### Scenario: Index reflects P4 complete

- **WHEN** a developer opens `docs/app/documentation.md` after this refresh
- **THEN** the header shows Through step ≥ P4.10 and the snapshot lists P3 search/enrich/index and P4 travel_engine + verification artifacts as present, with next product work described as P5.1 (not “build P3/P4”)

#### Scenario: Maintenance log records the catch-up

- **WHEN** the refresh is finished
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P4.10 (or equivalent) with trigger noting P3+P4 phase catch-up (or P4 phase complete)

### Requirement: Module map and wiring include P3 and P4 artifacts

The module map and imports/wiring pages MUST list as real (not stub): `src/search/*` (client, embeddings, places_index), place enrich path + `enriched_tags`, `scripts/enrich_places.py` / `scripts/index_places.py`, CORS middleware + `CORS_ALLOWED_ORIGINS`, all `src/travel_engine/*` modules through `trip_validator`, `src/planner/routing_provider.py`, `src/planner/tools/schemas.py` (`ToolResult`), `src/planner/tools/registry.py` (`execute_tool` envelope), `tests/travel_engine/` / `tests/planner/` / `tests/search/` as applicable, and `scripts/test_p4_smoke.py`. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (planner LangGraph / tool bodies, trips/evaluation except models, `auth/dependencies.py`).

#### Scenario: Junior looks up travel_engine

- **WHEN** a developer opens the module map looking for `travel_engine/`
- **THEN** they see the P4 pure-Python modules marked as real with no I/O claim, not as “stubs (later)”

#### Scenario: Junior looks up planner package

- **WHEN** a developer opens the module map looking for `planner/`
- **THEN** they see routing provider + tools envelope as real, and LangGraph / tool bodies explicitly stubbed pending P5

### Requirement: How-to-change recipes cover P3/P4 verification paths

Recipes MUST mention running `python scripts/test_p4_smoke.py` and `python -m pytest tests/` (including travel_engine / planner / search packages) where appropriate. Readiness recipes MUST note that `search_available` reflects live Qdrant availability (`is_qdrant_available`) after P3.6, while preserving the existing formula-true place_count floors for sparse vs limited-band scoring.

#### Scenario: Smoke recipe after P4

- **WHEN** a developer follows verification recipes after the refresh
- **THEN** they are directed to the P4 smoke script and pytest packages consistent with `docs/context.md`, not only P2 smoke

#### Scenario: Readiness search_available is live

- **WHEN** a developer reads readiness language in the manual
- **THEN** they learn `search_available` is the live Qdrant flag, not permanently False as in the P2-era snapshot

## MODIFIED Requirements

### Requirement: Module map with real vs stub

The manual MUST include a module/package map keyed to the repository layout, listing key files and responsibilities for implemented modules through the current “through step” marker, and MUST mark stub-only packages so juniors do not assume public APIs exist. After the P3+P4 catch-up refresh, the through-step marker MUST be at least P4.10 and MUST treat geo gateways, destinations/places HTTP, readiness (including live `search_available`), P3 search/enrich/index, CORS, full `travel_engine/*`, planner routing provider + tools envelope, and P2–P4 verification artifacts as real. Stub callouts MUST match `docs/context.md` (planner LangGraph / tool bodies; trips/evaluation except models; `auth/dependencies.py`).

#### Scenario: Stub packages are explicit

- **WHEN** a developer looks up planner LangGraph nodes or tool *bodies* while those remain stubs
- **THEN** the manual states they are placeholders without implemented public APIs

#### Scenario: Real geo modules are listed

- **WHEN** the “through step” is at least P2.2
- **THEN** `src/geo/geocoder.py` and `src/geo/overpass.py` appear as real gateways with their public entry points (`geocode`, `fetch_pois`)

#### Scenario: P2 verification modules are listed as real

- **WHEN** the “through step” is at least P2.10
- **THEN** `src/geo/osrm.py`, destinations/places routers and readiness, P2 pytest packages, and `scripts/test_p2_smoke.py` appear as real

#### Scenario: P3 and P4 modules are listed as real

- **WHEN** the “through step” is at least P4.10
- **THEN** `src/search/*`, enrich/index scripts, `src/travel_engine/*`, `OsrmRoutingProvider`, `ToolResult`/`execute_tool` envelope, and `scripts/test_p4_smoke.py` appear as real
