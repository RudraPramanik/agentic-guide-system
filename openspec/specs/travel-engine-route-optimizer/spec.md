## Purpose

Pure day-route ordering for the travel engine (P4 step 4.5). Travel times injected via `RoutingProvider`; no geo/network/DB/LLM I/O.

## Requirements

### Requirement: Route optimizer orders a day via injected RoutingProvider
The project SHALL provide `src/travel_engine/route_optimizer.py` with types `DroppedStop`, `OptimizeResult`, and async function `optimize_route(day_places, base_lat, base_lng, routing: RoutingProvider) -> OptimizeResult` as locked in `docs/steps/step4.md` step 4.5 and `docs/blueprint_final.md` v6.1.

`optimize_route` MUST:
- Return an empty `OptimizeResult` when `day_places` is empty
- Build waypoints as `(BASE_SENTINEL_ID, base_lat, base_lng)` plus each place’s `(id, lat, lng)`
- Call `routing.travel_matrix(waypoints)` **once per optimization attempt**
- Index legs with `legs_to_lookup` and brute-force all permutations of the day’s stops (≤ `MAX_PLACES_PER_DAY!`), scoring total travel as base→first plus consecutive stop-to-stop legs
- Pick the minimum total travel ordering; MUST NOT use a TSP solver package
- Keep `ordered` as `list[ScoredPlace]`; set `legs` to the **full pairwise** `RouteLeg` list returned by `travel_matrix` for that attempt (not only the consecutive chain), so schedule morning-reorder can look up arbitrary hops; set `total_travel_min` from the best consecutive-path score
- Treat a missing lookup edge as duration `10**9` (defensive)
- Import neither `src.geo`, httpx, LLM clients, SQLAlchemy, nor Qdrant

#### Scenario: Fake provider yields a complete ordered day
- **WHEN** `optimize_route` is called with three scored places and a FakeRoutingProvider that returns a full directed pairwise matrix
- **THEN** the result has `len(ordered) == 3`, `legs` equal in size to the full directed pairwise matrix among BASE + stops (12 for 3 stops), and no network I/O occurs

#### Scenario: Empty day short-circuits
- **WHEN** `day_places` is `[]`
- **THEN** the result has empty `ordered`, empty `legs`, `total_travel_min == 0`, empty `dropped_stops`, and `still_over_budget` is false

### Requirement: Route optimizer drop-retry surfaces dropped_stops
When the best permutation’s total travel exceeds `MAX_DAILY_TRAVEL_MIN`, `optimize_route` MUST drop the lowest-scored remaining stop (stable tie-break by name then id), append a `DroppedStop` with reason `exceeded_max_daily_travel`, and retry optimization, calling `travel_matrix` again each attempt. Drop-retry MUST continue while total travel exceeds the cap and more than one stop remains, up to `MAX_ROUTE_DROP_ATTEMPTS` (which MUST be large enough that a day of `MAX_PLACES_PER_DAY` stops can thin to a single stop). It MUST always return a best-effort ordered list plus accumulated `dropped_stops`. `still_over_budget` MUST be true only when the remaining ordered stops (including the single-stop case) still exceed `MAX_DAILY_TRAVEL_MIN`.

#### Scenario: Over-budget day records drops with reasons
- **WHEN** every permutation’s total travel exceeds `MAX_DAILY_TRAVEL_MIN` under a Fake provider
- **THEN** the result includes one or more `dropped_stops` entries each with `place_id` and reason `exceeded_max_daily_travel`, and still returns a best-effort `ordered` list

#### Scenario: Drop continues until under budget or one stop
- **WHEN** a multi-stop day remains over budget after the first few drops but a thinner subset is under the cap
- **THEN** drop-retry continues (within `MAX_ROUTE_DROP_ATTEMPTS`) until `total_travel_min <= MAX_DAILY_TRAVEL_MIN` or only one stop remains

#### Scenario: Single remaining stop may still be over budget
- **WHEN** even the last remaining stop’s base→stop travel exceeds `MAX_DAILY_TRAVEL_MIN`
- **THEN** no further drops occur, `still_over_budget` is true, and `len(ordered) == 1`

### Requirement: OptimizeResult includes post-order polylines
`OptimizeResult` MUST include:

- `leg_polylines: list[str | None]` — length equals `len(ordered)`; index `i` is the polyline into `ordered[i]` from the previous waypoint (base for `i=0`)
- `day_polyline: str | None` — aggregate polyline for base + all ordered stops in order

After the final winning ordered list is selected (after drop-retry settles), `optimize_route` MUST call `routing.route_polyline` for each consecutive pair in `[(base_lat, base_lng)] + stop coords`, then once for the full waypoint list. It MUST NOT call `route_polyline` inside the permutation scoring loop or for discarded drop-retry candidates. Empty `ordered` MUST leave both fields empty/None with no geometry calls. All-None polylines MUST NOT abort optimization.

#### Scenario: Three stops yield three leg polylines plus day
- **WHEN** optimize returns three ordered stops and `route_polyline` returns deterministic non-None strings
- **THEN** `len(leg_polylines) == 3` and `day_polyline` is not None

#### Scenario: Geometry failure is soft
- **WHEN** `route_polyline` returns `None` for all calls
- **THEN** optimize still returns ordered stops / legs / travel totals with all-None polyline fields and does not raise

#### Scenario: No geometry during permutation search
- **WHEN** a Fake provider counts `route_polyline` calls during an optimize with multiple permutations
- **THEN** call count is ≤ `len(ordered) + 1` for the returned result (not proportional to permutation count)
