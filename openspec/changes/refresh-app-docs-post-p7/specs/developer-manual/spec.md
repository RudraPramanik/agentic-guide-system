## ADDED Requirements

### Requirement: Manual refresh after P7 phase completion

After P7 is recorded complete in `docs/context.md` (Progress 7.0–7.6 ✅, next step operator VPS deploy / production packaging), the developer manual MUST be refreshed in the same docs-sync change (or immediately after). The index `docs/app/documentation.md` MUST set **Through step** to at least **P7.6** (or an equivalent post-P7 marker), bump **Last refreshed**, and update the snapshot so it no longer claims trip edit/replan HTTP, shared `populate_leg_polylines`, TripService day surgery, `rate_limit_trip_edit`, evaluation `mark_trip_edited` polish, or `scripts/test_p7_smoke.py` are unbuilt (when those rows are ✅ in context). The refresh MUST also clear residual “next = P7.1 / edit later” framing left from the P6.5 marker and point next work at operator VPS deploy via `docs/steps/blueprint_production.md` (or whatever Next step context records). The maintenance refresh log MUST record a phase-complete (or deferred catch-up) row covering through P7.6. If context has not yet marked all P7 steps ✅, Through step MUST NOT exceed the highest validated P7 (or residual P6) step in context.

#### Scenario: Index reflects P7 complete

- **WHEN** a developer opens `docs/app/documentation.md` after this refresh with context showing P7.6 done
- **THEN** the header shows Through step ≥ P7.6 (or post-P7) and the snapshot lists trip edit HTTP + shared polyline helper + P7 verification artifacts as present, with next product work described as operator VPS deploy / production packaging (not “build P7”)

#### Scenario: Maintenance log records the catch-up

- **WHEN** the refresh is finished for P7.6
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P7.6 (or equivalent) with trigger noting P7 phase complete (or P7 catch-up)

#### Scenario: Through-step does not overshoot context

- **WHEN** `docs/context.md` still lists an incomplete P7 step as Next
- **THEN** the manual Through step stays ≤ the highest ✅ step and does not claim unfinished modules as shipped

### Requirement: Module map and wiring include P7 artifacts

The module map and imports/wiring pages MUST list as real (not stub) whatever `docs/context.md` marks implemented for P7, including at minimum when ✅: `save_from_state` base prefs + `_resolve_base` (7.0), public `populate_leg_polylines` + optimizer wiring (7.1), TripService edit ops (`reorder_stops` / `remove_stop` / `add_stop` / `reoptimize_day`) with preserve-order schedule + TripEditEvent UoW + `mark_trip_edited` (7.2), trips edit HTTP four routes + `rate_limit_trip_edit` + `RateLimitedError` 429 (7.3), `tests/trips/test_edit_replan.py` (7.4), evaluation flag polish `get_latest_for_trip` / `mark_user_edited` (7.5), `scripts/test_p7_smoke.py` + import guards (7.6). Production packaging pointers (hosted embeddings backend, deploy SOP) MAY appear in snapshot/orientation when context records them. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (evaluation HTTP, `auth/dependencies.py`, and any deferred clarification-path evaluation note).

#### Scenario: Junior looks up trip edit HTTP

- **WHEN** a developer opens the module map looking for trip day-edit routes after context marks 7.3 ✅
- **THEN** they see reorder / remove / add / reoptimize as real with ownership + `rate_limit_trip_edit` notes, not as “P7 later”

#### Scenario: Junior looks up shared polyline helper

- **WHEN** a developer opens the module map looking for `populate_leg_polylines` after context marks 7.1 ✅
- **THEN** they see it as a real public helper used by optimize and edit paths, not as unbuilt

#### Scenario: Junior looks up P7 smoke

- **WHEN** a developer opens the module map looking for verification after context marks 7.6 ✅
- **THEN** they see `scripts/test_p7_smoke.py` and edit/replan pytest as real

### Requirement: How-to-change recipes cover P7 edit and verification paths

Recipes MUST mention running `python scripts/test_p7_smoke.py` (when context marks 7.6 ✅) and relevant pytest packages (`tests/trips/test_edit_replan.py`, evaluation flag tests) where appropriate. Recipes that mention trip edits MUST note: `require_auth` + ownership, user-keyed `rate_limit_trip_edit` (fail-open; dual OK with middleware IP), and the four live paths under `/api/v1/trips/{id}/days/...`. Recipes MUST NOT present evaluation HTTP as live. Recipes MAY point at `docs/steps/blueprint_production.md` / `docs/FE_guide.md` for deploy and FE contract without duplicating those docs.

#### Scenario: Smoke recipe after P7

- **WHEN** a developer follows verification recipes after the P7 refresh
- **THEN** they are directed to the P7 smoke script and trip edit/replan pytest packages consistent with `docs/context.md`

#### Scenario: Edit route guidance is present

- **WHEN** a developer reads how-to-change guidance for changing a trip day after P7
- **THEN** they learn the four edit endpoints exist, require auth/ownership, and are rate-limited via `rate_limit_trip_edit`

#### Scenario: No invented evaluation HTTP

- **WHEN** a developer reads how-to-change or live-endpoint guidance after P7
- **THEN** they do not find evaluation HTTP presented as a registered live route

### Requirement: Architecture docs light-touch after P7

`docs/app/system.md` and `docs/app/lld.md` MUST NOT retain factual claims that contradict post-P7 `docs/context.md` (e.g. trips “edit/replan HTTP later (P7)”, Build Progress “through P6.5” as the latest rollup, pattern catalog implying day surgery / preserve-order / trip-edit rate limit / shared polyline helper are unbuilt). Corrections MUST be minimal status/framing fixes — not architecture rewrites. Residual stubs (evaluation HTTP, `auth/dependencies.py`) MAY remain called out as future work. Production packaging / hosted embeddings MAY be noted briefly with a link to `docs/steps/blueprint_production.md` without copying the full SOP.

#### Scenario: system.md trips row matches reality

- **WHEN** a reader checks the `src/trips/` summary in `system.md` after P7 is complete in context
- **THEN** the row no longer claims edit/replan HTTP is only future work; evaluation HTTP may still be noted as stub

#### Scenario: lld.md pattern table marks shipped P7 patterns

- **WHEN** a reader checks the pattern catalog in `lld.md` for trip edit UoW / preserve-order schedule / user-keyed trip-edit rate limit / `populate_leg_polylines` after P7 complete
- **THEN** those rows are framed as shipped (or present), not as upcoming-only work

#### Scenario: system.md next-step framing matches context

- **WHEN** a reader checks Build Progress or equivalent rollup in `system.md` after post-P7 context
- **THEN** the rollup is at least through P7 (not stuck at P6.5) and does not claim P7 edit work is unfinished when context marks it ✅

## MODIFIED Requirements

### Requirement: Module map with real vs stub

The manual MUST include a module/package map keyed to the repository layout, listing key files and responsibilities for implemented modules through the current “through step” marker, and MUST mark stub-only packages so juniors do not assume public APIs exist. After the P7 catch-up refresh, the through-step marker MUST be at least P7.6 when context records P7 complete, and MUST treat geo gateways, destinations/places HTTP, readiness (including live `search_available`), P3 search/enrich/index, CORS, full `travel_engine/*`, planner routing provider, full P5 tools + orchestration + graph + PlannerService SSE bridge + P5 verification artifacts, full P6 trips HTTP + planner SSE generate + cache backends + polylines + P6 verification artifacts, and full P7 trip edit/replan HTTP + shared polyline helper + evaluation flag polish + P7 verification artifacts as real (when ✅ in context). Stub callouts MUST match `docs/context.md` (evaluation HTTP; `auth/dependencies.py`; any still-deferred clarification evaluation).

#### Scenario: Stub packages are explicit

- **WHEN** a developer looks up evaluation HTTP or `auth/dependencies.py` while those remain unbuilt
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

#### Scenario: P6 persistence and SSE modules are listed as real

- **WHEN** the “through step” is at least P6.5 (and context marks those steps ✅)
- **THEN** trips HTTP CRUD/GeoJSON/claim, `POST /api/v1/planner/generate`, cache backends, rate-limiter Redis/InMemory selection, route polylines, and `scripts/test_p6_smoke.py` appear as real

#### Scenario: P7 edit and replan modules are listed as real

- **WHEN** the “through step” is at least P7.6 (and context marks those steps ✅)
- **THEN** trip edit HTTP routes, `populate_leg_polylines`, TripService day surgery, `rate_limit_trip_edit`, evaluation `mark_trip_edited` polish, and `scripts/test_p7_smoke.py` appear as real
