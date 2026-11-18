## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §6.4–§6.5, §7.1, and §9 rows 4.4 and 4.7, plus this change's `proposal.md`, `design.md`, and the four delta specs. `docs/steps/step4.md` steps 4.4 and 4.7 are the shipped day allocator and trip validator. Do not re-implement them.
- [x] 1.2 Keep production edits to: `src/travel_engine/route_optimizer.py`; `src/planner/tools/build_route.py`, `reoptimize_routes.py`, `drop_weakest_stop.py`, `expand_poi_search.py`, `validate_itinerary.py`, `orchestration.py`; `src/planner/graph/messages.py`; `src/planner/graph/state.py` for optional `v2_findings` and `replan_progress_signature` only; tests under `tests/travel_engine` and `tests/planner`; `docs/context.md`; travel-engine rows in `docs/v8.2/repository_audit.md`; blueprint §9 row 4.4 wording only. Do not edit `RouteLeg`, `src/trips/service.py`, `PHASE_TOOLS`, `TOOL_REGISTRY`, finding codes, flag defaults, Alembic, or `requirements.txt`. Do not lower `MAX_ROUTE_DROP_ATTEMPTS`.

## 2. Return legs (row 4.4)

- [x] 2.1 Add `return_to_base: bool = False` to `optimize_route`. Default false scores base→first plus hops only, leaves `return_polyline` null, and still calls `populate_leg_polylines`. Do not change that helper's return type.
- [x] 2.2 When `return_to_base` is true, add the existing last-stop→`BASE_SENTINEL_ID` `RouteLeg` to the score, the drop budget, and `total_travel_min`. Keep the drop reason `exceeded_max_daily_travel` and the cap at `MAX_PLACES_PER_DAY - 1`. A missing return edge uses the existing `10**9` penalty. A return leg with `used_fallback` true is kept and does not raise. `ordered` must not contain the base sentinel.
- [x] 2.3 When `return_to_base` is true, request polylines in `optimize_route` itself: one per stop arrival, one return polyline, one closed day polyline (base + stops + base). `len(leg_polylines)` stays `len(ordered)`. All-null geometry does not raise. Call count stays ≤ `len(ordered) + 2` and stays out of the permutation loop.
- [x] 2.4 Confirm `route_optimizer.py` does not call `get_settings()` and does not contain `TRAVEL_ENGINE_V2_ENABLED`. Stop if a `RouteLeg` field is required.

## 3. Tool wiring

- [x] 3.1 `build_route`, `reoptimize_routes`, `drop_weakest_stop`, and `expand_poi_search` read `TRAVEL_ENGINE_V2_ENABLED` only through `get_settings()` and pass `return_to_base` equal to that flag. Keep passing the same flag into `allocate_days` and `build_day_schedule`. Do not revert rows 4.3, 4.5, or 4.6.
- [x] 3.2 Flag off: route day `return_polyline` is null and `total_travel_min` is the open-jaw total. Flag on: `return_polyline` is the return geometry or null, and `total_travel_min` includes the return. `used_osrm_fallback` stays true when any leg, including the return, has `used_fallback`. Do not add a base stop to `ordered`.
- [x] 3.3 Leave `src/trips/service.py` on the default `return_to_base=False` call.

## 4. Replan mapping (row 4.7)

- [x] 4.1 Add `choose_replan_tool` beside orchestration. Legal names are only `reoptimize_routes`, `drop_weakest_stop`, and `expand_poi_search`. Blocking findings win; ties follow `FINDING_CODES` order. Ignore null and any other string. Do not register a tool.
- [x] 4.2 Add `v2_findings` to the orchestration merge set, and write it onto state only when `TRAVEL_ENGINE_V2_ENABLED` is true. Flag off must leave state without that key. Do not change `VALIDATOR_V2_ENFORCE` or make `validate_itinerary` call a REPLAN tool.
- [x] 4.3 When the engine flag is on and validation is not ok with replan budget left, store `replan_progress_signature` (finding-code multiset plus dropped place ids) and set `force_next_tool` from `choose_replan_tool`. If the signature is unchanged, set `force_next_tool` to `accept_partial` instead of another repair. Exhausted `PLANNER_MAX_REPLAN_ATTEMPTS` still goes to WRAP_UP with `abort_triggered` and forces no repair. Flag off does not set `force_next_tool` from findings.
- [x] 4.4 When the engine flag is on and the REPLAN stuck path would abort, set `force_next_tool` to `accept_partial` and do not jump to WRAP_UP in that branch. Flag off keeps `phase_stuck_replan_abort`. Do not edit the agent node; it already consumes `force_next_tool`.
- [x] 4.5 `build_agent_messages`: flag off keeps the expand-over-drop sentence when `dropped_stops` is present. Flag on names the chosen repair tool when one exists, includes each drop reason string, and does not name a tool outside the REPLAN list. Do not present `accept_partial` as the mapped repair.

## 5. Feature tests and terminal transcript

- [x] 5.1 Add FakeRoutingProvider tests for return mode off (open-jaw total, null `return_polyline`, polyline calls ≤ `len(ordered) + 1`), return mode on (total includes last→base, `return_polyline` set, calls ≤ `len(ordered) + 2`), fallback return leg kept, and round-trip over budget recording `exceeded_max_daily_travel`.
- [x] 5.2 Add planner tests: flag-off `build_route` stays open-jaw; flag-on `build_route` and `reoptimize_routes` pass return mode on; flag-off validate does not publish `v2_findings` onto state; flag-on validate does; enforce false still does not change `ok` when `validate_trip` passes; a blocking finding forces its existing tool; an unknown action is ignored; an unchanged signature forces `accept_partial`; exhausted replan budget does not force a repair; flag-off REPLAN messages still prefer `expand_poi_search` when drops exist; flag-on messages contain the mapped tool and `exceeded_max_daily_travel`.
- [x] 5.3 Add a transcript test that prints one fake day in both modes (order, base→first minutes, hops, last→base minutes, total, drop reasons, return polyline null or set) and prints one replan decision (`finding code → tool`, then unchanged signature → `accept_partial`). Run it with stdout visible (`pytest -s` on that test). Quote those lines in the completion note in task 6.3.
- [x] 5.4 Run `pytest tests/travel_engine -k "optimizer or return" -v` and `pytest tests/planner -v`. Both must exit 0. If a full planner run is already red for a reason outside this change, stop and report that failure. Do not weaken a flag-off assertion to make it pass.

## 6. Slice 1–4 exam and sync

- [x] 6.1 Run the existing exit-gate commands at default flags and record pass or fail: `pytest tests/planner/runs -v`, `pytest tests/trips tests/planner -k idempotent -v`, `pytest tests/location_intelligence -v`, `pytest tests/travel_engine -v`, and `python scripts/run_evals.py --replay`. Do not pass `--update-baseline`.
- [x] 6.2 Write the exam into `docs/v8.2/repository_audit.md` as a short Slice 1–4 completeness note: what those commands showed, plus the open items that this change does not close (Slice 2 golden case-count expansion, FE location picker, `VALIDATOR_V2_ENFORCE` soak, and the Slice 4 gate that wants improvement on at least two of duplicate rate, schedule feasibility, and coherence). Do not mark that Slice 4 exit gate done unless the replay shows it.
- [x] 6.3 Update `docs/context.md`: rows 4.4 and 4.7 done behind `TRAVEL_ENGINE_V2_ENABLED` (default false); quote the task 5.3 transcript; point Next step at the exam's first real gap. Do not mark full Slice 4 exit done. Align blueprint §9 row 4.4 only: shipped drop cap, existing `base_lat`/`base_lng` as the trip base, and no new `RouteLeg` field.
