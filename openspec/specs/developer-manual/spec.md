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
The manual MUST include a module/package map keyed to the repository layout, listing key files and responsibilities for implemented modules through the current “through step” marker, and MUST mark stub-only packages so juniors do not assume public APIs exist. After the P2 phase-complete refresh, the through-step marker MUST be at least P2.10 and MUST treat geo gateways, destinations/places HTTP, readiness, P2 pytest modules, and `scripts/test_p2_smoke.py` as real.

#### Scenario: Stub packages are explicit
- **WHEN** a developer looks up `planner/`, `search/`, or `travel_engine/` while those remain stubs
- **THEN** the manual states they are placeholders without implemented public APIs

#### Scenario: Real geo modules are listed
- **WHEN** the “through step” is at least P2.2
- **THEN** `src/geo/geocoder.py` and `src/geo/overpass.py` appear as real gateways with their public entry points (`geocode`, `fetch_pois`)

#### Scenario: P2 verification modules are listed as real
- **WHEN** the “through step” is at least P2.10
- **THEN** `src/geo/osrm.py`, destinations/places routers and readiness, P2 pytest packages, and `scripts/test_p2_smoke.py` appear as real

### Requirement: Manual refresh after P2 phase completion
After P2.9 and P2.10 are recorded complete in `docs/context.md`, the developer manual MUST be refreshed in the same docs-sync change (or immediately after). The index `docs/app/documentation.md` MUST set **Through step** to at least **P2.10**, bump **Last refreshed**, and update the snapshot so it no longer claims P2 pytest or `scripts/test_p2_smoke.py` are unbuilt. The maintenance refresh log MUST record a phase-complete row for P2.

#### Scenario: Index reflects P2 complete
- **WHEN** a developer opens `docs/app/documentation.md` after this refresh
- **THEN** the header shows Through step ≥ P2.10 and the snapshot lists P2 pytest packages and the P2 smoke script as present, with next product work described as P3+ (not “build 2.9/2.10”)

#### Scenario: Maintenance log records the phase end
- **WHEN** the refresh is finished
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P2.10 (or equivalent) with trigger “P2 phase complete”

### Requirement: Module map and wiring include P2 verification artifacts
The module map and imports/wiring pages MUST list as real (not stub): `tests/geo/`, `tests/destinations/`, `tests/places/`, `tests/scripts/`, `scripts/test_p2_smoke.py`, and the seed pipeline helper `seed_destination_into` alongside existing `seed_places` / `seed_destination`. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (planner, search, travel_engine, trips/evaluation except models, `auth/dependencies.py`).

#### Scenario: Junior looks up P2 tests
- **WHEN** a developer opens the module map looking for P2 tests
- **THEN** they see the geo/destinations/places/scripts test packages and the P2 smoke script marked as real, not “lands in 2.9–2.10”

### Requirement: How-to-change recipes stay formula-true on readiness
Recipes that mention destination readiness after seed MUST distinguish Overpass/seed volume (`place_count >= 50`) from unenriched limited-band scoring (`place_count >= 100` preferred; `>= 88` minimum for score ≥ 0.35). They MUST NOT imply that `place_count >= 50` alone yields `tier=limited`.

#### Scenario: Seed recipe mentions readiness band
- **WHEN** a developer follows the seed / readiness recipe
- **THEN** they are told volume ≥50 is not sufficient for limited-band claims and to use a larger radius (e.g. `--radius 50`) when they need ~100+ places for `tier=limited`

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
