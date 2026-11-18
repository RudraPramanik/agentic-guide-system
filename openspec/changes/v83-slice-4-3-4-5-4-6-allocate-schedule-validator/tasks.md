## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.4–§6.5, §7.1, §8.3–§8.4, §9 rows 4.3, 4.5, and 4.6, plus this change's `proposal.md`, `design.md`, and delta specs under `specs/`. There is no `docs/steps/step*.md` for these rows. Do not treat `docs/steps/step4.md` steps 4.3 / 4.5 / 4.6 as this task.
- [x] 1.2 Keep production edits to: `src/travel_engine/day_allocator.py`, `schedule_builder.py`, `trip_validator.py`, `findings.py` (new), `place_selector.py` (hours fields only), `travel_rules.py`, `src/planner/tools/build_route.py`, `build_schedule.py`, `validate_itinerary.py`, `src/config.py`, `.env.example`, `tests/travel_engine/**`, planner tool tests, `tests/architecture/_helpers.py` only if it lists flag defaults, `docs/v8.2/allocator_v2_comparison.md`, `docs/context.md`, and travel-engine/flag rows in `docs/v8.2/repository_audit.md`. Do not edit `route_optimizer.py`, `trips/service.py`, replan tools, FE docs, Alembic, or `requirements.txt`. Do not rename `PlaceCandidate.id`.

## 2. Allocator comparison (row 4.3, before any tune)

- [x] 2.1 Write `docs/v8.2/allocator_v2_comparison.md` from the current `allocate_days`: 10 km pre-cluster, `MAX_PLACES_PER_DAY`, visit budget `8 * 60 - MIN_TRAVEL_BUFFER_MIN`, morning-only cap, and the far-cluster omission. State whether any constant misses the row. Do not change engine code in this task.
- [x] 2.2 If the report names no miss, leave `CLUSTER_RADIUS_KM`, `MAX_PLACES_PER_DAY`, and `ACTIVE_DAY_VISIT_BUDGET_MIN` unchanged. If it names a miss, tune only that miss behind `v2_enabled=True` and record it in the same note. Stop if the tune needs a new clustering library.

## 3. Settings and rules data

- [x] 3.1 Add `VALIDATOR_V2_ENFORCE: bool = False` on `Settings`. Comment that the tool reads it via `get_settings()` and the engine must not. If `tests/architecture/_helpers.py` enumerates flag defaults, add this flag as false.
- [x] 3.2 Document `VALIDATOR_V2_ENFORCE=false` in `.env.example` next to `TRAVEL_ENGINE_V2_ENABLED`. Do not change the engine flag default.
- [x] 3.3 Add `DAY_END_TIME = "16:00"` to `travel_rules.py` (eight hours after `DAY_START_TIME`). Do not add a parser or a timezone.

## 4. Candidate hours fields

- [x] 4.1 Add optional `opening_hours_status` (default `unknown`), `opening_open`, and `opening_close` on `PlaceCandidate`. Existing payloads must still validate. Scoring must ignore the fields. Do not parse OSM hours.

## 5. Allocator mode

- [x] 5.1 Add `v2_enabled: bool = False` to `allocate_days`. Mode off or omitted must return today's day membership. Mode on must keep the place cap, visit budget, morning cap, and the rule that a place farther than `CLUSTER_RADIUS_KM` does not join an occupied day when an empty or nearer day can take it. If task 2.2 found no miss, mode on calls the same packing body.
- [x] 5.2 Keep `day_allocator.py` free of `get_settings`, the two setting names, geo, HTTP, DB, and LLM imports.

## 6. Schedule V2 (row 4.5)

- [x] 6.1 Split the current clock into the legacy path. `v2_enabled` defaults false and matches today's times, including `preserve_order=True`.
- [x] 6.2 When `v2_enabled` is true and `preserve_order` is false, advance each hop by `RouteLeg.duration_min + MIN_TRAVEL_BUFFER_MIN`, keep one lunch and the morning-only extract, and omit a stop whose visit would end after `DAY_END_TIME`. Do not replace leg duration with a fixed spacing constant. Times stay naive `"HH:MM"`.
- [x] 6.3 Verified status plus open/close: wait until open only when the visit still ends by close and by `DAY_END_TIME`; otherwise omit the stop. Unknown, malformed, or absent status must not move the stop and must not claim it is open. `preserve_order=True` ignores V2 omission and hour waits.
- [x] 6.4 Stop if the implementation needs a timezone or a new package.

## 7. Findings and validator (row 4.6)

- [x] 7.1 Add `src/travel_engine/findings.py` with `Severity`, `ValidationFinding`, and a registry of exactly the sixteen §6.5 codes. `blocks_publish` and `suggested_action` follow `design.md` decision 4. `suggested_action` is null or one of `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`. The module must not call tools or import I/O.
- [x] 7.2 Add `collect_findings` beside `validate_trip`. Reuse the existing check predicates for travel cap, repeats, morning slots, anchor, and geo coherence. Implement the other codes from `design.md` decision 4, including optional search center/radius, geometry-promised, and leg durations. Do not change `validate_trip` string errors, warnings, or `passed`.
- [x] 7.3 Do not import `SearchArea`. When radius is absent, do not emit `OUT_OF_SEARCH_AREA`. Stop if the collector needs network, DB, or an LLM.

## 8. Tool wiring

- [x] 8.1 `build_route` reads `TRAVEL_ENGINE_V2_ENABLED` via `get_settings()` and passes `v2_enabled` into every `allocate_days` call. Do not pass it into `optimize_route`.
- [x] 8.2 `build_schedule` passes the same flag into `build_day_schedule` with `preserve_order` false.
- [x] 8.3 `validate_itinerary` calls `collect_findings` on every non-empty itinerary. While `VALIDATOR_V2_ENFORCE` is false, `ok`, `errors`, `warnings`, and `validation_result` match `validate_trip` only. Return findings as `data["v2_findings"]` and log them. Do not add that key to orchestration `_MERGE_KEYS`. While the flag is true, `ok` is false when `passed` is false or any finding has `blocks_publish` true. Pass search center/radius only when `state["search_area"]` has those numbers. Do not call a REPLAN tool.
- [x] 8.4 Leave `trips/service.py` on the default schedule and `validate_trip` calls.

## 9. Tests

- [x] 9.1 Allocator tests: default call matches current membership; far cluster stays off a near day; mode-on days respect the caps; mode-on coherence kilometers are less than or equal to mode-off on one shared fixture, using the existing coherence metric.
- [x] 9.2 Schedule tests: mode-off matches current times; V2 hop is leg duration plus `MIN_TRAVEL_BUFFER_MIN`; day-end omission; unknown hours do not delay or claim open; verified window can wait until open; preserve-order ignores V2; start times stay strictly increasing.
- [x] 9.3 Findings tests: registry length and names; each of the sixteen codes has one invalid fixture that emits it and one valid fixture that does not; unknown hours are not `OPENING_HOURS_CONFLICT`; missing search area does not emit `OUT_OF_SEARCH_AREA`; a repeated place id emits `DUPLICATE_STOP`; an over-cap day still has the v6.1 string error and `EXCESSIVE_TRAVEL_TIME` with `blocks_publish` false.
- [x] 9.4 Tool tests: flag-off `build_route` allocates with mode off; flag-on `build_schedule` calls V2 mode; enforce false keeps `ok` true when `validate_trip` passes even if a blocking finding exists; enforce true sets `ok` false for a `blocks_publish` finding. Patch settings in the test. Do not change the default.
- [x] 9.5 Update `tests/travel_engine/test_properties.py` so the engine scan rejects both setting names and `get_settings`, and the cap property still calls `allocate_days` without V2 mode.

## 10. Verify and completion sync

- [x] 10.1 Run `pytest tests/travel_engine -k "allocator or schedule or validator or findings" -v`, then `pytest tests/travel_engine -v`, then the planner tool tests touched above. All exit 0.
- [x] 10.2 Run `python scripts/run_evals.py --replay` with both flags at their defaults. Exit 0 and no new regression. Do not flip either default to true. If replay fails because findings entered `validation_result` or a merged state key, stop and remove that merge. Do not `--update-baseline` to hide it.
- [x] 10.3 Run `pytest tests/architecture -v`. Confirm `src/travel_engine/**` still passes purity / G2 and does not contain either setting name.
- [x] 10.4 Update `docs/context.md`: rows 4.3, 4.5, and 4.6 done behind the flags (engine flag still default false, enforce default false); next blueprint feature rows are 4.4 and 4.7. Update `docs/v8.2/repository_audit.md` for the comparison note, findings module, and `VALIDATOR_V2_ENFORCE`. Do not mark the full Slice 4 exit gate done.
- [x] 10.5 Confirm the diff stays inside task 1.2 paths. No Alembic, no `requirements.txt`, no FE/OpenAPI change, no `route_optimizer.py` edit. Put the blueprint §19 completion report in the PR description.
