## MODIFIED Requirements

### Requirement: Route optimizer orders a day via injected RoutingProvider
The project SHALL provide `src/travel_engine/route_optimizer.py` with types `DroppedStop`, `OptimizeResult`, and async function `optimize_route(day_places, base_lat, base_lng, routing: RoutingProvider, *, return_to_base: bool = False) -> OptimizeResult` as locked in `docs/steps/step4.md` step 4.5 and `docs/blueprint_final.md` v6.1, extended by blueprint v8.3 §9 row 4.4.

`optimize_route` MUST:
- Return an empty `OptimizeResult` when `day_places` is empty, including `return_polyline` null, whether or not `return_to_base` is true
- Build waypoints as `(BASE_SENTINEL_ID, base_lat, base_lng)` plus each place’s `(id, lat, lng)`
- Call `routing.travel_matrix(waypoints)` **once per optimization attempt**
- Index legs with `legs_to_lookup` and brute-force all permutations of the day’s stops (≤ `MAX_PLACES_PER_DAY!`), scoring total travel as base→first plus consecutive stop-to-stop legs, plus the leg from the last ordered stop to `BASE_SENTINEL_ID` only when `return_to_base` is true
- Pick the minimum total travel ordering; MUST NOT use a TSP solver package
- Keep `ordered` as `list[ScoredPlace]` and MUST NOT insert the base sentinel into `ordered`; set `legs` to the **full pairwise** `RouteLeg` list returned by `travel_matrix` for that attempt (not only the consecutive chain), so schedule morning-reorder can look up arbitrary hops; set `total_travel_min` from the best consecutive-path score, including the return leg only when `return_to_base` is true
- Treat a missing lookup edge, including a missing return edge, as duration `10**9` (defensive)
- Default `return_to_base` to false. The module MUST NOT call `get_settings()` and MUST NOT contain the setting name `TRAVEL_ENGINE_V2_ENABLED`
- Adapt to the existing `RouteLeg` fields (`from_place_id`, `to_place_id`, `duration_min`, `distance_km`, `used_fallback`). It MUST NOT add or rename a `RouteLeg` field
- Keep a return leg whose `used_fallback` is true. That leg MUST NOT raise and MUST NOT be discarded
- Import neither `src.geo`, httpx, LLM clients, SQLAlchemy, nor Qdrant

#### Scenario: Fake provider yields a complete ordered day
- **WHEN** `optimize_route` is called with three scored places, `return_to_base` false, and a FakeRoutingProvider that returns a full directed pairwise matrix
- **THEN** the result has `len(ordered) == 3`, `legs` equal in size to the full directed pairwise matrix among BASE + stops (12 for 3 stops), `return_polyline` is null, and no network I/O occurs

#### Scenario: Empty day short-circuits
- **WHEN** `day_places` is `[]`
- **THEN** the result has empty `ordered`, empty `legs`, `total_travel_min == 0`, empty `dropped_stops`, `still_over_budget` is false, and `return_polyline` is null

#### Scenario: Default mode excludes the return leg from the score
- **WHEN** `return_to_base` is false and the matrix contains a last-stop→base leg with a positive duration
- **THEN** `total_travel_min` equals base→first plus the consecutive stop hops and does not include that return duration

#### Scenario: Return mode adds the last-stop to base leg
- **WHEN** `return_to_base` is true and the matrix contains a leg from the chosen last stop to `BASE_SENTINEL_ID`
- **THEN** `total_travel_min` includes that leg’s `duration_min`, `ordered` does not contain `BASE_SENTINEL_ID`, and the `RouteLeg` still has only the existing fields

#### Scenario: Fallback return leg is kept
- **WHEN** `return_to_base` is true and the return leg has `used_fallback` true
- **THEN** optimization returns that leg inside `legs`, does not raise, and still sets `total_travel_min` from it

### Requirement: Route optimizer drop-retry surfaces dropped_stops
When the best permutation’s total travel exceeds `MAX_DAILY_TRAVEL_MIN`, `optimize_route` MUST drop the lowest-scored remaining stop (stable tie-break by name then id), append a `DroppedStop` with reason `exceeded_max_daily_travel`, and retry optimization, calling `travel_matrix` again each attempt. Drop-retry MUST continue while total travel exceeds the cap and more than one stop remains, up to `MAX_ROUTE_DROP_ATTEMPTS` (which MUST remain `MAX_PLACES_PER_DAY - 1` and MUST NOT be lowered to 3, so a day of `MAX_PLACES_PER_DAY` stops can thin to a single stop). It MUST always return a best-effort ordered list plus accumulated `dropped_stops`. `still_over_budget` MUST be true only when the remaining ordered stops (including the single-stop case) still exceed `MAX_DAILY_TRAVEL_MIN`. The total compared with the cap MUST be the scored total from the order requirement, so a return leg counts only when `return_to_base` is true. The drop reason MUST stay `exceeded_max_daily_travel`.

#### Scenario: Over-budget day records drops with reasons
- **WHEN** every permutation’s total travel exceeds `MAX_DAILY_TRAVEL_MIN` under a Fake provider and `return_to_base` is false
- **THEN** the result includes one or more `dropped_stops` entries each with `place_id` and reason `exceeded_max_daily_travel`, and still returns a best-effort `ordered` list

#### Scenario: Drop continues until under budget or one stop
- **WHEN** a multi-stop day remains over budget after the first few drops but a thinner subset is under the cap
- **THEN** drop-retry continues (within `MAX_ROUTE_DROP_ATTEMPTS`) until `total_travel_min <= MAX_DAILY_TRAVEL_MIN` or only one stop remains

#### Scenario: Single remaining stop may still be over budget
- **WHEN** even the last remaining stop’s base→stop travel exceeds `MAX_DAILY_TRAVEL_MIN` and `return_to_base` is false
- **THEN** no further drops occur, `still_over_budget` is true, and `len(ordered) == 1`

#### Scenario: Return mode can drop when the round trip exceeds the cap
- **WHEN** `return_to_base` is true and base→stop fits the cap but base→stop→base exceeds it for every multi-stop order
- **THEN** drop-retry records reason `exceeded_max_daily_travel` and the surviving total includes the return leg

### Requirement: OptimizeResult includes post-order polylines
`OptimizeResult` MUST include:

- `leg_polylines: list[str | None]` — length equals `len(ordered)`; index `i` is the polyline into `ordered[i]` from the previous waypoint (base for `i=0`)
- `day_polyline: str | None` — aggregate polyline for the waypoint list below
- `return_polyline: str | None` — polyline for the last ordered stop back to the base point when `return_to_base` is true; otherwise null

After the final winning ordered list is selected (after drop-retry settles), `optimize_route` MUST call `routing.route_polyline` for each consecutive pair in the open-jaw list `[(base_lat, base_lng)] + stop coords` when `return_to_base` is false, then once for that full list. When `return_to_base` is true it MUST also call `route_polyline` for the last stop back to `(base_lat, base_lng)` and the day polyline MUST cover base + ordered stops + base. It MUST NOT call `route_polyline` inside the permutation scoring loop or for discarded drop-retry candidates. Empty `ordered` MUST leave polyline fields empty/None with no geometry calls. All-None polylines MUST NOT abort optimization. `len(leg_polylines)` MUST stay equal to `len(ordered)` in both modes.

#### Scenario: Three stops yield three leg polylines plus day
- **WHEN** optimize returns three ordered stops, `return_to_base` is false, and `route_polyline` returns deterministic non-None strings
- **THEN** `len(leg_polylines) == 3`, `day_polyline` is not None, and `return_polyline` is null

#### Scenario: Geometry failure is soft
- **WHEN** `route_polyline` returns `None` for all calls
- **THEN** optimize still returns ordered stops / legs / travel totals with all-None polyline fields and does not raise

#### Scenario: No geometry during permutation search
- **WHEN** a Fake provider counts `route_polyline` calls during an optimize with multiple permutations and `return_to_base` false
- **THEN** call count is ≤ `len(ordered) + 1` for the returned result (not proportional to permutation count)

#### Scenario: Return mode adds one return polyline and closes the day line
- **WHEN** `return_to_base` is true, optimize returns two ordered stops, and `route_polyline` returns deterministic non-None strings
- **THEN** `len(leg_polylines) == 2`, `return_polyline` is not None, and `route_polyline` call count is ≤ `len(ordered) + 2`
