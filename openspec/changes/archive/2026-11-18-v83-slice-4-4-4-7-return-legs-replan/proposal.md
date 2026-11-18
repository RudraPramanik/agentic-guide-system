## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **4.4** and **4.7**) is the remaining Slice 4 feature work. Rows 4.1–4.2 are archived. Rows 4.3, 4.5, and 4.6 are implemented behind `TRAVEL_ENGINE_V2_ENABLED` (default false) and `VALIDATOR_V2_ENFORCE` (default false) in change `v83-slice-4-3-4-5-4-6-allocate-schedule-validator`, and that change explicitly left 4.4 and 4.7 undone. The optimizer still scores base→first plus stop hops and never the return to the trip base. Validator findings carry a `suggested_action`, but REPLAN does not read it, does not record drop reasons in the agent prompt, and treats a stuck replan as an abort string rather than the existing `accept_partial` tool.

`docs/steps/step4.md` steps 4.4 and 4.7 are the already-shipped P4 day allocator and trip validator. They are not this task. `docs/context.md` marks those P4 steps done and correctly names v8.3 rows 4.4 and 4.7 as next.

## What Changes

- Row **4.4**: keep permutation search, `dropped_stops` with reason `exceeded_max_daily_travel`, and the shipped drop cap `MAX_ROUTE_DROP_ATTEMPTS` (`MAX_PLACES_PER_DAY - 1`, which is 5). When an injected return mode is on, include the existing last→base `RouteLeg` in the score, the drop budget, and `total_travel_min`, and request a return polyline. `RouteLeg` is not redefined. Injected-off output stays the current open-jaw day (base→first + hops, no return polyline).
- Row **4.7**: when the engine flag is on, map a finding's `suggested_action` onto an existing REPLAN tool (`reoptimize_routes`, `drop_weakest_stop`, or `expand_poi_search`), force that tool, keep `PLANNER_MAX_REPLAN_ATTEMPTS`, and on no progress force the existing `accept_partial`. Record each `dropped_stops` reason in the REPLAN prompt. Flag off leaves today's prompt and transitions.
- After those rows, run the Slice 1–4 verification commands already defined by their exit gates and record what is complete versus what is still open. That exam does not add product behavior.
- No **BREAKING** change to HTTP paths, SSE event names, GeoJSON, `RouteLeg`, flag-off optimizer output, or flag-off REPLAN behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `travel-engine-route-optimizer`: injected return-to-base mode; flag-equivalent off path unchanged; `RouteLeg` unchanged; haversine fallback legs still accepted.
- `planner-plan-replan-tools`: route and replan tools pass the injected return mode from `TRAVEL_ENGINE_V2_ENABLED`; `v2_findings` merge onto state only when that flag is on.
- `planner-agent-messages`: engine-flag-on REPLAN prompt names the mapped tool and the drop reasons; flag off keeps the current expand-over-drop sentence.
- `planner-phase-orchestration`: engine-flag-on REPLAN forces the mapped existing tool, and no progress forces `accept_partial`; the locked flag-off transition table stays.

## Impact

- **Work surface:** `guideagent` only. No frontend change and no parent-vault symptom.
- **Code:** `src/travel_engine/route_optimizer.py`; planner callers `build_route.py`, `reoptimize_routes.py`, `drop_weakest_stop.py`, `expand_poi_search.py`; `src/planner/tools/validate_itinerary.py` and `orchestration.py`; `src/planner/graph/messages.py`; `src/planner/graph/state.py` only if the findings list needs a typed optional key. Tests under `tests/travel_engine` and `tests/planner`. Completion notes in `docs/context.md` and `docs/v8.2/repository_audit.md`.
- **Trip edits** (`src/trips/service.py`) keep calling `optimize_route` with return mode off. Slice 6.4 and 9.3 own edit and lodging-base reoptimization.
- **No new package.** No `requirements.txt` change. No Alembic revision. No new setting. No HTTP/SSE contract change.
- **Evals:** default-flag `python scripts/run_evals.py --replay` must stay non-regressing. This change does not claim the Slice 4 golden-improvement exit gate unless that replay shows it.

## Non-goals

- No re-implementation of P4 step 4.4 (`day_allocator`) or P4 step 4.7 (`trip_validator`).
- No new finding code, no change to the §6.5 registry, and no change to which code maps to which `suggested_action`. `accept_partial` stays off that field.
- No new planner tool, no change to `PHASE_TOOLS` or `TOOL_REGISTRY`, and no raise of `PLANNER_MAX_REPLAN_ATTEMPTS` or `PLANNER_GENERATION_TIMEOUT_SECONDS`.
- No shrink of `MAX_ROUTE_DROP_ATTEMPTS` to 3.
- No `RouteLeg` field, no second route model, and no base stop inserted into the schedule or the ordered place list.
- No polygon containment, no opening-hours parser, no timezone, and no flip of `VALIDATOR_V2_ENFORCE` or `TRAVEL_ENGINE_V2_ENABLED` defaults. Enforce soak stays an operator decision from row 4.6.
- No Slice 5–9 work, no FE contract, and no rewrite of blueprint §9.
- The Slice 1–4 exam records gaps. It does not fix Slice 2 case-count expansion, the FE location picker, or an unmet golden-improvement number inside this change.

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep `travel_engine/` free of I/O, `get_settings()`, geo, SQLAlchemy, HTTP, and LLM imports (G2). The return mode is an injected boolean, same pattern as `v2_enabled` on the allocator and schedule.
- Read `TRAVEL_ENGINE_V2_ENABLED` only through `get_settings()` at the planner tool boundary (N2, G3, G11). Default remains false.
- Leave critical findings deterministic. The repair tool is chosen from `suggested_action`, not from the model (N3, N4).
- Keep one canonical stop list. A return leg is a `RouteLeg` to `BASE_SENTINEL_ID`, not a new stop (N5).
- Preserve flag-off optimizer totals, leg lists, polyline counts, and REPLAN messages (N1, G13).

Checkout notes, confirmed against the tree. These do **not** rewrite the blueprint. Say so before apply if one of them should become a blueprint edit:

- Row 4.4 says "3-attempt cap". The shipped cap is `MAX_ROUTE_DROP_ATTEMPTS = MAX_PLACES_PER_DAY - 1` (5), and the locked optimizer spec requires thinning a full day to one stop. This change keeps 5. A hard cap of 3 would violate that spec. The blueprint cell should say "shipped drop cap" if it is edited later.
- Row 4.4's path cell names only `route_optimizer.py`. Call sites that must pass the injected boolean are the same wiring exception used for rows 4.1–4.6: the planner tools above. `messages.py` is already in row 4.7's path cell. `orchestration.py` is under `src/planner/tools/**`.
- "When trip base set" has no separate column. §6 legacy mapping says trip base is `base_lat`/`base_lng`, and the router already fills those from the destination center when the client omits them. Return mode follows `TRAVEL_ENGINE_V2_ENABLED`, not a new "base was explicit" flag. A lodging base that is distinct from that point is row 9.3.
- Row 4.4 stop line is a `RouteLeg` schema change. This design does not change `RouteLeg`. The return edge is already in the pairwise matrix (`last stop` → `BASE_SENTINEL_ID`). `used_fallback` on that leg stays the routing adapter's haversine mark. The optimizer does not invent a second fallback.
- `leg_polylines` stays aligned to ordered stops (length equals `len(ordered)`). The return geometry is a new optional `return_polyline` on `OptimizeResult`, null when return mode is off, so schedule stop `i` still copies `leg_polylines[i]`.
- Row 4.6 left `v2_findings` off `TravelState` on purpose. Row 4.7 is the consumer. Merge that key only when the engine flag is on so flag-off state stays as it is today.
- Schedule V2 does not gain a second drop pass. `total_travel_min` already flows from the optimizer into the schedule day dict, so a return that is inside the optimizer total is inside the day budget the validator already reads. Omitting a stop only in the schedule would desync the route. Wall-clock past `DAY_END` because of the ride back is repaired later by the existing replan tools, not by a new finding code.
- Row 4.7 stop line is a new tool. Every repair name already exists. If a finding carries any other string, ignore it and do not register a tool.
