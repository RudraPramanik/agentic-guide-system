## 1. Protocol + providers

- [x] 1.1 Add `route_polyline` to `RoutingProvider` in `src/travel_engine/protocols.py` (fail-soft docstring; no I/O)
- [x] 1.2 Implement `OsrmRoutingProvider.route_polyline` wrapping existing `get_route`; return None on fallback / missing geometry / any exception
- [x] 1.3 Add `route_polyline` to `tests/travel_engine/fake_routing.py` (deterministic placeholder); update `scripts/test_p4_smoke.py` fake if it implements the Protocol

## 2. Optimizer geometry

- [x] 2.1 Extend `OptimizeResult` with `leg_polylines` and `day_polyline`
- [x] 2.2 After final winning order (post drop-retry), populate polylines via `routing.route_polyline` (N pair calls + 1 full-path); skip geometry on empty ordered and on discarded retry attempts
- [x] 2.3 Unit tests: three-stop alignment; all-None soft-fail; empty day zero calls; call-count ≤ len(ordered)+1

## 3. Schedule shape + tool threading

- [x] 3.1 Document locked day-dict `schedule` shape on `TravelState` in `src/planner/graph/state.py`
- [x] 3.2 `build_route`: copy `leg_polylines` / `day_polyline` onto each route day dict from `OptimizeResult`
- [x] 3.3 `build_schedule`: emit list of day dicts (flat stops with `place_id`, order, times, `leg_polyline`, plus `day` / `day_polyline` / travel totals) — retire `list[list[stop]]`
- [x] 3.4 Update `validate_itinerary` to accept day-dict schedule and reconstruct `ScheduledStop`/`DayPlan`
- [x] 3.5 Ensure `write_narrative` structural copy preserves `day_polyline` (and stop `leg_polyline` via `stops`)

## 4. Verification + context

- [x] 4.1 Run step 6.0 validation snippet from `docs/steps/step6.md` (PASS polyline threading)
- [x] 4.2 Run failure path: all-None polylines, no exception
- [x] 4.3 Run `python -m pytest tests/travel_engine tests/planner -q` green; full `tests/` if feasible
- [x] 4.4 Update `docs/context.md`: mark 6.0 done, Next step → 6.1; note schedule day-dict + `route_polyline` real; do not mark all of P6 complete
