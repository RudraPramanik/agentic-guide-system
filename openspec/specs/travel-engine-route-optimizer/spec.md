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
- Keep `ordered` as `list[ScoredPlace]`; set `legs` to the consecutive `RouteLeg` chain for the chosen order (base→first, then each hop); set `total_travel_min` accordingly
- Treat a missing lookup edge as duration `10**9` (defensive)
- Import neither `src.geo`, httpx, LLM clients, SQLAlchemy, nor Qdrant

#### Scenario: Fake provider yields a complete ordered day
- **WHEN** `optimize_route` is called with three scored places and a FakeRoutingProvider that returns a full directed pairwise matrix
- **THEN** the result has `len(ordered) == 3`, consecutive `legs` length 3, and no network I/O occurs

#### Scenario: Empty day short-circuits
- **WHEN** `day_places` is `[]`
- **THEN** the result has empty `ordered`, empty `legs`, `total_travel_min == 0`, empty `dropped_stops`, and `still_over_budget` is false

### Requirement: Route optimizer drop-retry surfaces dropped_stops
When the best permutation’s total travel exceeds `MAX_DAILY_TRAVEL_MIN`, `optimize_route` MUST drop the lowest-scored remaining stop (stable tie-break by name then id), append a `DroppedStop` with reason `exceeded_max_daily_travel`, and retry optimization up to `MAX_ROUTE_DROP_ATTEMPTS` times (each retry calls `travel_matrix` again). It MUST always return a best-effort ordered list plus accumulated `dropped_stops`. If still over the cap after max drops, `still_over_budget` MUST be true.

#### Scenario: Over-budget day records drops with reasons
- **WHEN** every permutation’s total travel exceeds `MAX_DAILY_TRAVEL_MIN` under a Fake provider
- **THEN** the result includes one or more `dropped_stops` entries each with `place_id` and reason `exceeded_max_daily_travel`, and still returns a best-effort `ordered` list

#### Scenario: Drop attempts are capped
- **WHEN** a day remains over budget after `MAX_ROUTE_DROP_ATTEMPTS` drops
- **THEN** no further drops occur and `still_over_budget` is true
