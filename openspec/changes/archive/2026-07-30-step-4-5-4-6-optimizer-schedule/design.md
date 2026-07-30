## Context

Implement P4 steps **4.5–4.6** from the locked build contract `docs/steps/step4.md`. Planner SoT remains `docs/blueprint_final.md` v6.1 (Template Method + RoutingProvider DI; Configuration-as-data in `travel_rules`; Adapter for OSRM deferred to 4.8). Do **not** revise step4, step4-fix, or the blueprint in this change.

**Already shipped:** `protocols.py` (`RouteLeg`, `RoutingProvider`, `legs_to_lookup`), `travel_rules.py` (caps, `BASE_SENTINEL_ID`, `MAX_DAILY_TRAVEL_MIN`, `MAX_ROUTE_DROP_ATTEMPTS`, morning/lunch constants, `visit_duration_min`), `place_selector.py` (`ScoredPlace`, `PlaceCandidate`), `day_allocator.py`. Stubs remain: `route_optimizer.py`, `schedule_builder.py` (~1-line placeholders).

**Doc guidance:** Use `step4.md` as the only implementation contract. Fix-log locks for brute-force ordering, drop-retry visibility, naive wall-clock times, and morning-only placement are already in step4 — no parallel design from `step4-fix.md`.

## Goals / Non-Goals

**Goals:**
- Ship `route_optimizer` (4.5) and `schedule_builder` (4.6) exactly per step4 prompts and blueprint patterns.
- Pass each step’s ✅ validation; keep travel_engine pure (routing injected; no `src.geo` / httpx / LLM / DB).
- Land focused pytest for both modules covering step 4.9 ★ cases for optimizer/schedule (Fake provider offline).
- Bump `docs/context.md` for 4.5–4.6 only; Next step = 4.7.

**Non-Goals:**
- Steps 4.7–4.10 (validator, OsrmRoutingProvider, tools envelope, full suite, smoke, P4-complete context).
- HTTP, SQLAlchemy Place mapping, planner tools, LangGraph.
- Any TSP / OR-Tools / `python-tsp` dependency.
- Continuing or applying stale archived `p4-travel-engine` tasks that contradict v6.1.

## Decisions

### D1 — Build contract is step4.md only
Copy types/APIs from steps 4.5–4.6. Reuse `ScoredPlace` / `PlaceCandidate` from `place_selector`; reuse `RouteLeg` / `RoutingProvider` / `legs_to_lookup` from `protocols`; constants only from `travel_rules`. No SQLAlchemy models. No geo imports.

### D2 — Template Method + DI (blueprint pattern)
`optimize_route` owns the fixed algorithm skeleton; the only injectable step is `await routing.travel_matrix(waypoints)`. Callers (tests now; P5 `build_route` later) pass a `RoutingProvider`. This batch does **not** implement `OsrmRoutingProvider`.

### D3 — Matrix once per attempt + brute-force permutations
Locked algorithm for `optimize_route`:
1. Empty `day_places` → empty `OptimizeResult` (`ordered=[]`, `legs=[]`, `total_travel_min=0`, `dropped_stops=[]`, `still_over_budget=False`).
2. Build waypoints = `[(BASE_SENTINEL_ID, base_lat, base_lng), *[(p.place.id, p.place.lat, p.place.lng) for p in remaining]]`.
3. `matrix = await routing.travel_matrix(waypoints)` **once per attempt** (including after each drop).
4. `lookup = legs_to_lookup(matrix)`.
5. Enumerate all permutations of remaining stops (≤ `MAX_PLACES_PER_DAY!` = 720). For each order, total travel = `leg(BASE → first) + sum(leg(stop_i → stop_{i+1}))`.
6. Pick minimum total travel. On equal totals, prefer the lexicographically smaller sequence of place ids (deterministic). **No** TSP package.
7. Missing lookup edge → treat duration as `10**9` (defensive; providers MUST return full directed pairwise legs).

**Alternatives considered:** nearest-neighbor / TSP library — rejected by step4 Decision Log #3 and blueprint (nondeterministic / new package).

### D4 — Drop-retry surfaces `dropped_stops`
If best total > `MAX_DAILY_TRAVEL_MIN` and drops so far < `MAX_ROUTE_DROP_ATTEMPTS`:
- Drop the **lowest-scored** remaining stop (stable tie-break: name, then id).
- Append `DroppedStop(place_id=..., name=..., reason="exceeded_max_daily_travel")`.
- Retry from waypoint rebuild (new matrix call).
Always return best-effort ordered stops + accumulated `dropped_stops`. Set `still_over_budget=True` if final best total still exceeds the cap.

`OptimizeResult.legs` MUST be the **consecutive** chain for the chosen order: `legs[0]` = base→ordered[0]; `legs[i]` = ordered[i-1]→ordered[i] for i≥1; `len(legs) == len(ordered)`.

**Alternatives considered:** silent drop without reasons — rejected (Decision Log #4); REPLAN needs visibility to prefer `expand_poi_search`.

### D5 — FakeRoutingProvider lives in tests
A deterministic Fake implementing `travel_matrix` (dict or duration function → full pairwise `RouteLeg` list) lives under `tests/` (helper module or conftest). Production adapter is 4.8. Unit tests MUST NOT hit the network.

### D6 — Schedule: naive clock + lunch + morning-only
Locked algorithm for `build_day_schedule(ordered_stops, route_legs)`:

1. Empty `ordered_stops` → `[]`.
2. Build lookup via `legs_to_lookup(route_legs)`. Common path: `len(route_legs) == len(ordered_stops)` (consecutive chain from optimizer). Larger lists are allowed as lookup-complete pairwise sets. Non-empty stops with too few legs → `ValueError` with a clear message.
3. **Morning extract (before first timing):** if any stop’s `category` is in `MORNING_ONLY_CATEGORIES`, stable-extract morning-only stops to the front (preserve relative order among morning-only and among others); place `k = min(2, n_morning)` in slots 0..k-1. Document in module docstring. If extract changes order and a required hop is missing from lookup (`BASE_SENTINEL_ID → first` and each consecutive pair) → `ValueError` (do not invent durations; do not call geo).
4. **Timing:** start at `DAY_START_TIME`. For stop 0, add base→first travel from lookup/`legs[0]` before setting `suggested_start_time`. For each stop: record start; advance by `visit_duration_min(category)`; then advance by travel to the next stop when present.
5. **Lunch:** if adding the next visit would cross `LUNCH_BREAK_START`, insert `LUNCH_BREAK_MIN` once before that visit (`arrival_note` MAY mention lunch).
6. Never attach timezone / UTC. Local `"HH:MM"` parse/add helpers only.

**Apply note:** unit tests that move a late viewpoint should either start with the viewpoint already early, or pass lookup-complete pairwise legs so extract+recompute succeeds. P5 may re-optimize after extract if consecutive-only legs are insufficient — out of this batch’s code scope, but documented here.

### D7 — Wall-clock helpers are local pure functions
Parse `"HH:MM"` ↔ minutes-from-midnight; format back. Prefer minute arithmetic over `datetime.now`. Durations always via `visit_duration_min(category)`.

### D8 — Tests land with this batch
Create `tests/travel_engine/test_route_optimizer.py` and `test_schedule_builder.py` with ★ cases from step 4.9 that apply. Include Fake provider, over-budget drop-retry, morning viewpoint slot, lunch gap, mismatched legs `ValueError`. Full purity/CORS/validator suites remain 4.9.

## Risks / Trade-offs

- [Risk] Morning extract changes order while caller passed consecutive-only legs for the pre-extract order → `ValueError` → Mitigation: D6 pre-timing extract + tests supply matching/pairwise legs; P5 can re-optimize later.
- [Risk] Permutation nondeterminism on equal totals → Mitigation: lex smaller place-id sequence tie-break (D3).
- [Risk] Accidental geo import or TSP package → Mitigation: purity scan; assert requirements have no tsp/ortools.
- [Trade-off] Full travel_engine pytest tree waits for 4.9 → Acceptable; this batch owns optimizer/schedule files.
- [Risk] Drop lowest-score removes the day’s only anchor → Mitigation: out of scope (validator 4.7 + REPLAN); `dropped_stops` makes it visible.

## Migration Plan

1. Implement 4.5 route_optimizer + Fake helper + step validation + pytest  
2. Implement 4.6 schedule_builder + step validation + pytest  
3. Update context.md progress (Next → 4.7)  
4. Rollback: revert the two modules + tests; stubs can be restored

## Open Questions

None — step4 locks + D3–D6 are sufficient for apply.
