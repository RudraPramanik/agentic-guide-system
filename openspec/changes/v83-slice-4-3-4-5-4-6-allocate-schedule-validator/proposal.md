## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **4.3**, **4.5**, and **4.6**, with contracts in §6.4–§6.5 and flags in §7.1) is the next feature slice after rows 4.1–4.2. There is no `docs/steps/step*.md` for these rows. `docs/steps/step4.md` steps 4.3 / 4.5 / 4.6 are the already-shipped P4 selector, optimizer, and schedule modules; they are not this task. Allocation, scheduling, and validation still follow the v6.1 path even when `TRAVEL_ENGINE_V2_ENABLED` is on, and there is no structured finding registry or `VALIDATOR_V2_ENFORCE` shadow. This change makes those three rows feature-proof behind the existing engine flag and a new enforce flag that stays off.

## What Changes

- Row **4.3**: compare the current `day_allocator` to the locked 10 km pre-cluster, `MAX_PLACES_PER_DAY`, and 8 h visit budget, and write that comparison before any tune. Keep flag-off packing identical. A far cluster stays off a day that already holds another region. No new clustering library.
- Row **4.5**: when V2 mode is injected, time days from real `RouteLeg.duration_min` values plus configured buffers, one lunch, morning-only slots, and verified hours only. Naive `"HH:MM"` stays. Unknown or missing hours are not treated as open. Flag-off timing stays the current builder.
- Row **4.6**: add pure `ValidationFinding` records for every §6.5 code, with severity, `blocks_publish`, `repairable`, and a deterministic `suggested_action` drawn only from today's REPLAN tool names. Existing v6.1 string checks stay. `VALIDATOR_V2_ENFORCE` defaults false: findings are computed and logged, and they do not change `ok`, `errors`, or `validation_result`. Enforce-on is implemented and tested; the default is not flipped.
- No **BREAKING** change to HTTP paths, SSE event names, GeoJSON, flag-off day lists, flag-off schedules, or flag-off validation results.

## Capabilities

### New Capabilities

- `travel-engine-findings`: pure finding model, stable §6.5 code registry, and the closed `suggested_action` set. No I/O.

### Modified Capabilities

- `travel-engine-day-allocator`: injected V2 mode after a written comparison; flag-off packing unchanged; caps and the far-cluster rule stay.
- `travel-engine-schedule-builder`: injected V2 timing (real legs, buffer, lunch, morning-only, verified hours, fits the day); flag-off timing unchanged.
- `travel-engine-trip-validator`: v6.1 chain retained; V2 findings produced beside it; shadow versus enforce does not live inside the engine as a settings read.
- `travel-engine-place-selector`: additive optional hours fields on `PlaceCandidate` only. Scoring behavior unchanged.
- `travel-engine-rules`: day-end and hours-related constants as data. Existing caps and weights stay.
- `travel-engine-properties`: allocator, schedule, and validator may take an injected mode; engine source still must not name the settings or call `get_settings()`.
- `planner-plan-replan-tools`: `build_route` and `build_schedule` pass the existing engine flag into allocate and schedule; `validate_itinerary` reads `VALIDATOR_V2_ENFORCE` and keeps the v6.1 publish decision while the flag is false.

## Impact

- **Work surface:** `guideagent` only. No frontend OpenSpec change and no parent-vault symptom.
- **Code:** `src/travel_engine/day_allocator.py`, `schedule_builder.py`, `trip_validator.py`, `findings.py` (new), `place_selector.py` (optional fields), `travel_rules.py`, `src/planner/tools/build_route.py`, `build_schedule.py`, `validate_itinerary.py`, `src/config.py`, `.env.example`, `tests/travel_engine/**`, planner tool tests for the two flags.
- **Completion sync:** comparison note plus `docs/context.md` and the travel-engine / flag rows in `docs/v8.2/repository_audit.md` after verify commands pass. No other doc. No rewrite of blueprint §9.
- **No new package.** No `requirements.txt` change. No Alembic revision. No HTTP/SSE contract change.
- **Evals:** `pytest tests/travel_engine -k "allocator or schedule or validator"` and `python scripts/run_evals.py --replay` must stay non-regressing with both flags at their defaults.

## Non-goals

- No row **4.4** (base→first / last→base optimizer legs, `RouteLeg` changes). Schedule V2 consumes durations already on `RouteLeg`.
- No row **4.7** (replan loop, prompt mapping, `dropped_stops` reason wiring). `suggested_action` is data only.
- No Slice **5.3** opening-hours parser, no new dependency, no timezone, no date or seasonal logic (§8.3–§8.4).
- No rename of `PlaceCandidate.id` to `place_id`. No second candidate or itinerary model.
- No import of `SearchArea`, geo, SQLAlchemy, HTTP, or LLM into `travel_engine/`.
- No FE contract, no OpenAPI change, no trip column.
- No Slice 5–9 work. The enforce flag default stays false. Rollback is flag off.

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep `travel_engine/` free of I/O, `get_settings()`, geo, SQLAlchemy, HTTP, and LLM imports (G2). Tools inject booleans and plain area numbers.
- Read `TRAVEL_ENGINE_V2_ENABLED` and `VALIDATOR_V2_ENFORCE` only through `get_settings()` at the planner tool boundary (N2).
- Preserve flag-off allocator output, schedule output, and `validate_trip` pass/errors (N1). Shadow findings must not change `validation_result`, `errors`, or `ToolResult.ok` while enforce is false.
- Keep critical findings deterministic. A judge or score cannot clear them (N3). This change does not add a judge.
- Treat missing hours, missing search area, and missing geometry mode as unknown. Do not invent an open window, an area, or a road geometry (N6).
- Stop if a clustering library, a timezone, an opening-hours package, or a validator I/O import is required (rows 4.3, 4.5, 4.6 stop lines).

Checkout notes, confirmed against the tree rather than treated as a halt. These do **not** rewrite the blueprint. Say so before apply if one of them should become a blueprint edit:

- `CLUSTER_RADIUS_KM` is already 10. `MAX_PLACES_PER_DAY` is already 6. `ACTIVE_DAY_VISIT_BUDGET_MIN` is already `8 * 60 - MIN_TRAVEL_BUFFER_MIN` (450), not a looser 480. The far-cluster omission from the Slice 2.5 gate correction is already in `allocate_days`. Row 4.3's compare-first step may conclude there is no constant to change. In that case V2 mode must match today's packing, and the proof is the report plus cap and coherence tests. Do not loosen the 450-minute budget to "make it 8 hours."
- §8.3 and row 5.3 own OSM parsing. Row 4.5 still requires verified-hours behavior. This change adds optional `opening_hours_status` (default `unknown`) and optional naive open/close strings on `PlaceCandidate`. Only `verified` plus a supplied window may move or drop a V2 stop. No parser.
- §9 path cells name the engine modules only. `config.py`, `.env.example`, `build_route.py`, and `build_schedule.py` are the same settings/wiring exception used for rows 4.1–4.2. `place_selector.py` changes only to hold the optional hours fields.
- `suggested_action` may be only `reoptimize_routes`, `drop_weakest_stop`, or `expand_poi_search`, or null. `accept_partial` is not a suggested repair. Wiring that name into the REPLAN loop is row 4.7.
- Trip edit scheduling (`trips/service.py`) keeps calling `build_day_schedule` and `validate_trip` with defaults, so preserve-order edits stay on the v6.1 path.
- "Enforce after shadow soak" is an operator decision. This change ships the enforce code path and leaves the default false.
