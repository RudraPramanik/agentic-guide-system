## Context

See proposal.md for why v8.3 rows 4.4 and 4.7 are the remaining Slice 4 feature work. `optimize_route` already puts `BASE_SENTINEL_ID` in the matrix and scores base→first plus hops. The last→base `RouteLeg` is already in that matrix and is unused by the score. `RouteLeg` stays `from_place_id`, `to_place_id`, `duration_min`, `distance_km`, `used_fallback`.

`validate_itinerary` already returns `v2_findings`, and `apply_tool_result` drops that key because it is not in `_MERGE_KEYS`. `force_next_tool` is already honored by the agent node. REPLAN tools and `accept_partial` are already registered. `PLANNER_MAX_REPLAN_ATTEMPTS` is 2.

Rows 4.3, 4.5, and 4.6 are in the working tree behind the two existing flags. Their OpenSpec change is complete and not yet archived. This design must not revert injected `v2_enabled` on allocate and schedule, shadow findings, or `VALIDATOR_V2_ENFORCE` default false. The sentence in that change which says tools must not pass the engine flag into `optimize_route` is superseded only for the new `return_to_base` boolean.

No new external call is introduced. Routing failure stays the adapter's haversine `used_fallback` on `RouteLeg`. `route_polyline` already soft-fails to null. The optimizer does not add a timeout, a retry, or a second fallback.

## Goals / Non-Goals

**Goals:**

- Default `return_to_base=False` keeps today's open-jaw totals, drop behavior, and polyline call counts.
- Flag-on days include the return in the score, the drop budget, `total_travel_min`, and a separate `return_polyline`.
- Flag-on REPLAN forces one existing repair tool from `suggested_action`, records drop reasons, and forces `accept_partial` when that repair does not change the finding codes or the dropped place ids.
- A terminal transcript and a Slice 1–4 exam show what is actually true after the tests, without new product behavior in the exam.

**Non-Goals:**

- Editing `src/trips/service.py`, `RouteLeg`, `PHASE_TOOLS`, finding codes, or flag defaults.
- A second schedule drop pass. Schedule days keep copying `total_travel_min` from the optimizer result.
- Claiming the Slice 4 golden-improvement exit gate inside the exam.

## Decisions

### 1. Return mode is a keyword on `optimize_route`, default false

`return_to_base: bool = False`. `_score_order` adds the last-stop→`BASE_SENTINEL_ID` duration only when it is true. Missing edge stays the existing `10**9` penalty. Drop reason stays `exceeded_max_daily_travel`. Cap stays `MAX_ROUTE_DROP_ATTEMPTS` (5).

The module must not mention `TRAVEL_ENGINE_V2_ENABLED` or call `get_settings()`.

Alternative considered: always add the return. Rejected because flag-off replay and the locked open-jaw spec would change. Alternative considered: a new `RouteLeg` role field. Rejected because row 4.4 stops if `RouteLeg` must change.

### 2. Do not change `populate_leg_polylines`'s return type

That helper returns `(leg_polylines, day_polyline)` and is unpacked by trip edits and polyline tests for the open jaw. Leave it. When `return_to_base` is false, `optimize_route` keeps calling it. When true, `optimize_route` requests polylines itself: one call per stop arrival, one last→base call stored as `return_polyline`, one closed day call (base + stops + base). Count is at most `len(ordered) + 2`. `leg_polylines` length stays `len(ordered)`. Null geometry does not raise.

`OptimizeResult.return_polyline` defaults to null so existing constructors stay valid.

### 3. One flag at the tool boundary

`build_route`, `reoptimize_routes`, `drop_weakest_stop`, and `expand_poi_search` read `TRAVEL_ENGINE_V2_ENABLED` through `get_settings()` and pass `return_to_base=flag`. They keep passing that same flag into `allocate_days` and `build_day_schedule`. Flag off: route day dicts leave `return_polyline` null and do not add the key if that would change a snapshot; null is the required value. Flag on: set `return_polyline` and the return-inclusive `total_travel_min`. `used_osrm_fallback` stays true if any leg, including the return, has `used_fallback`.

There is no new "user typed a base" bit. The coordinates already on the tool are the trip base, including the router's destination-center fill. A distinct lodging base waits for row 9.3.

Trip edits keep the default `return_to_base=False` by not being edited.

### 4. One chooser for the mapped tool

Add a pure function next to orchestration, for example `choose_replan_tool(findings) -> str | None`. It imports the existing `FINDING_CODES` order. It ignores null and any name other than `reoptimize_routes`, `drop_weakest_stop`, and `expand_poi_search`. Blocking findings win; ties use registry order. `messages.py` and `maybe_transition_phase` both call it so the prompt and `force_next_tool` cannot disagree.

`build_agent_messages` reads the flag through `get_settings()`. Flag off: keep the current expand-over-drop sentence and do not print finding actions. Flag on: name the chosen tool when one exists, and print every dropped-stop reason already stored on the route day (`exceeded_max_daily_travel`). Do not tell the model to call `accept_partial` as the repair. No-progress forcing is orchestration's job, not a prompt invention.

Do not edit the agent node. It already turns `force_next_tool` into the next pending call and clears the field.

### 5. Findings merge and no-progress signature

Add `v2_findings` to `_MERGE_KEYS`, but `apply_tool_result` writes it only when the engine flag is true. Flag off leaves state without that key even though the tool result still carries the list.

On entry to REPLAN with budget left and the flag on, store a signature of the multiset of finding codes plus the set of dropped place ids (state field `replan_progress_signature`, optional on `TravelState`). Set `force_next_tool` to `choose_replan_tool(...)`. If this entry's signature equals the stored one, set `force_next_tool` to `accept_partial` instead. Exhausted budget still goes to WRAP_UP with `abort_triggered` and does not force a repair. Flag off does not set `force_next_tool` from findings and does not compare signatures.

When the flag is on and the stuck detector would abort REPLAN, set `force_next_tool` to `accept_partial` and do not jump to WRAP_UP in that branch, so the existing tool runs and the trace shows it. Flag off keeps `phase_stuck_replan_abort`.

`accept_partial` itself is unchanged.

### 6. Terminal proof and the Slice 1–4 exam

Add a focused test that prints a fixed fake day: ordered names, base→first minutes, each hop, last→base minutes, total, drop reasons, and `return_polyline` present or null in both modes. Add a planner test that prints the mapped tool for one blocking finding and then `accept_partial` when the signature does not change. Run those tests with output enabled and quote the lines in `docs/context.md`.

The exam runs the existing exit-gate commands (planner runs and idempotency, travel-engine tests, location tests, `python scripts/run_evals.py --replay` at default flags). Record pass/fail and the known open items: Slice 2 case-count expansion, FE location picker, enforce soak, and the Slice 4 golden improvement on at least two of duplicate rate, schedule feasibility, and coherence. Do not update baselines. Do not fix an exam gap that is outside rows 4.4 and 4.7.

### 7. Blueprint wording that this design does not adopt

- "3-attempt cap" stays the shipped cap of 5. Changing it would fail the locked thin-to-one-stop rule.
- Row path cells stay as written. The extra files are the tool wiring, orchestration, state typing, tests, and the two completion docs.
- No blueprint edit in this change. A later doc edit can replace "3-attempt cap" with "shipped drop cap" and can name the tool files. That edit is not required to implement the specs.

## Risks / Trade-offs

- [Return minutes make more flag-on days over the 180-minute cap] → Drop-retry already records `exceeded_max_daily_travel`. Flag off is unchanged. Do not raise the cap.
- [Schedule clock still ends at the last stop, so the ride back can pass `DAY_END` without dropping that stop] → Accepted. A second drop only in the schedule would desync route and schedule. The return is in `total_travel_min`, which the validator already reads. Repair stays the existing replan tools.
- [Morning-only reorder can change which stop is last after the optimizer scored the return] → Pre-existing for the outbound leg too. This change does not retune morning extraction.
- [Forcing `accept_partial` on a stuck REPLAN skips the old immediate WRAP_UP] → Only when the engine flag is on. The tool's own success path still sets `abort_triggered` and WRAP_UP. Flag off is the rollback.
- [Merging `v2_findings` changes planner state when the flag is on] → The flag defaults false. SSE event names and GeoJSON are not given this key. Do not put the list on the public itinerary.
- [4.3–4.6 specs are not archived yet] → Implement against the code and this delta. Do not delete injected allocator or schedule mode while adding `return_to_base`.

## Migration Plan

No migration and no new setting. `TRAVEL_ENGINE_V2_ENABLED` stays false, so production behavior stays the open-jaw optimizer and the current REPLAN prompt. Rollback is that flag off. `VALIDATOR_V2_ENFORCE` stays false.

## Open Questions

None. The blueprint wording mismatches in Decision 7 are decided for this change. They do not change the specs or the task list. A blueprint edit is optional and waits for an explicit request.
