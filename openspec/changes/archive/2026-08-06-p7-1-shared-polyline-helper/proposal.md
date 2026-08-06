## Why

P7 reorder must recompute polylines for a **caller-decided** stop order without calling `optimize_route`. Today that geometry loop is private (`_populate_polylines`), so a future TripService path would either duplicate it or accidentally collapse `OptimizeResult.legs` into consecutive-only. Step **7.1** (`docs/steps/step7.md`) promotes the helper now — while P7.0 is done and before 7.2 day surgery — so generation and reorder share one fail-soft implementation.

## What Changes

- Promote `_populate_polylines` to a public (or module-documented) async helper, e.g. `populate_leg_polylines(ordered, base_lat, base_lng, routing)`, in `src/travel_engine/route_optimizer.py`.
- Refactor `optimize_route` to call that helper after the winning order is final (behavior-preserving).
- Keep `OptimizeResult.legs` as the **full pairwise** matrix from `travel_matrix` — **not** consecutive-only.
- Optionally add a thin fixed-order consecutive-legs helper in the same module if useful for 7.2 (separate from `OptimizeResult.legs`); wire-up of TripService reorder stays in 7.2.
- Extend/confirm tests: three-stop Fake optimize → full pairwise `legs` length + aligned `leg_polylines`; all-None polylines still succeed.
- Update `docs/context.md` after validation (Next → 7.2).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `travel-engine-route-optimizer`: Fulfill and tighten the existing “shared polyline population” requirement — public helper name, `optimize_route` must call it, legs remain full pairwise, soft-fail None polylines unchanged. Add explicit pairwise-size scenario for the three-stop Fake case.

## Impact

- **Code:** `src/travel_engine/route_optimizer.py` only (per step 7.1). No trips router/service edits, no HTTP, no planner tools, no LLM, no migration, no new packages.
- **AGENT.md:** travel_engine purity (RoutingProvider only; no geo/httpx/DB); extend don’t replace P0–P6 behavior.
- **Callers:** generation path via `optimize_route` unchanged externally; 7.2 will import the shared helper for reorder.
- **Tests:** `tests/travel_engine/` (route optimizer / polyline suite) must stay green.
- **Non-goals:** edit HTTP endpoints; preserve-order schedule; `TripService` day surgery; changing drop-retry / permutation scoring; inventing DayPlan/ScheduledStop polyline fields; wiring reorder callers (7.2).
