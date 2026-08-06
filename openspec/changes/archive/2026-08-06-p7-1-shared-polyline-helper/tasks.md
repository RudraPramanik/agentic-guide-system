## 1. Promote shared polyline helper

- [x] 1.1 Read `AGENT.md`, `docs/context.md`, and `docs/steps/step7.md` §7.1 before coding
- [x] 1.2 In `src/travel_engine/route_optimizer.py`, promote `_populate_polylines` to public `populate_leg_polylines` (same signature/behavior: ordered + base + RoutingProvider → leg_polylines + day_polyline; empty → `([], None)`)
- [x] 1.3 Refactor `optimize_route` to call `populate_leg_polylines` for the winning order only; keep `OptimizeResult.legs` as full pairwise matrix from `travel_matrix`
- [x] 1.4 Grep: no remaining callers of `_populate_polylines`; no duplicate polyline for-loops; no trips/HTTP/planner edits

## 2. Tests

- [x] 2.1 Confirm or extend Fake three-stop optimize: `len(legs) == 12` and `len(leg_polylines) == 3`
- [x] 2.2 Confirm all-None `route_polyline` still returns ordered OptimizeResult without raise
- [x] 2.3 Add or extend a direct `populate_leg_polylines` call for two ordered stops (len==2, soft-fail OK)
- [x] 2.4 Run `python -m pytest tests/travel_engine/ -v` green

## 3. Close out

- [x] 3.1 Update `docs/context.md`: mark 7.1 ✅, Next → 7.2, note public `populate_leg_polylines` in implemented modules
- [x] 3.2 Do not implement 7.2 edit ops or preserve-order schedule in this change
