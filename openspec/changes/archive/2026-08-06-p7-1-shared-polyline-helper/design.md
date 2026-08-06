## Context

P7.0 is done (`save_from_state` persists `base_lat`/`base_lng`; `_resolve_base` ready). Next build contract step is **7.1** in `docs/steps/step7.md`: promote the private polyline loop so generation and a future fixed-order reorder path share one implementation.

Today `optimize_route` calls `_populate_polylines` only after the winning order is final. `OptimizeResult.legs` is already the full pairwise matrix (not consecutive-only). The risk locked in the step prompt is inventing a “shared legs helper” that accidentally collapses legs — this change shares **polyline** population only.

Constraints: `travel_engine/` purity (RoutingProvider only); no new packages; no trips/HTTP/planner edits in this step.

## Goals / Non-Goals

**Goals:**

- Public async helper `populate_leg_polylines(ordered, base_lat, base_lng, routing) -> (leg_polylines, day_polyline)` with the same N+1 soft-fail `route_polyline` pattern as today.
- `optimize_route` calls that helper for the final ordered list; external optimize behavior unchanged.
- `OptimizeResult.legs` remains full pairwise matrix size (e.g. 12 for BASE + 3 stops).
- Tests green; optional thin fixed-order consecutive-legs helper only if it clarifies 7.2 without changing `OptimizeResult.legs`.

**Non-Goals:**

- TripService reorder / remove / add / reoptimize (7.2)
- Preserve-order schedule builder (7.2)
- Edit HTTP routes or rate limits (7.3)
- Changing drop-retry, permutation scoring, or DayPlan/ScheduledStop shapes
- Wiring the helper into trips domain yet (import-only readiness for 7.2)

## Decisions

1. **Public name `populate_leg_polylines`**
   - **Choice:** Rename/promote `_populate_polylines` to `populate_leg_polylines` (keep private alias only if something external already imported the private name — today nothing should).
   - **Why:** Matches step 7.1 contract; makes the 7.2 import surface obvious.
   - **Alternatives:** Keep private + re-export thin wrapper — more noise for one caller family.

2. **Share polyline only — not legs**
   - **Choice:** Helper returns polylines only. Consecutive RouteLeg chains for reorder stay separate (optional `compute_fixed_order_legs` or live in TripService in 7.2).
   - **Why:** Critics lock #17 — naive “shared legs helper” collapses full matrix semantics schedule morning-extract needs.
   - **Alternatives:** One mega helper returning matrix + consecutive + polylines — rejected as over-abstraction (forward lock F5).

3. **Optional fixed-order legs helper**
   - **Choice:** Defer unless it is a trivial extract of existing consecutive-chain logic already in the module; prefer shipping polyline promote alone if optional helper risks scope creep.
   - **Why:** Step marks it optional; 7.2 can own the matrix-once consecutive path.

4. **Validation**
   - **Choice:** Rely on existing Fake optimize tests + assert `len(legs)==12` and `len(leg_polylines)==3` for three stops; soft-fail all-None case; run `pytest tests/travel_engine/`.
   - **Why:** Step ✅ validation; no new packages or HTTP fixtures.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Refactor accidentally sets `legs` to consecutive only | Spec + test: pairwise size 12 for 3 stops; do not change how `legs` is assigned |
| Duplicate polyline loops appear in 7.2 anyway | Document helper as the only allowed geometry path; 7.2 tasks must import it |
| Optional fixed-order helper confuses with `OptimizeResult.legs` | If added, docstring MUST say consecutive-only and “not OptimizeResult.legs” |
| Rename breaks private imports | Grep for `_populate_polylines`; only `optimize_route` should call it today |

## Migration Plan

- Pure refactor inside one module; no DB/API migration.
- Rollback = revert the file; no data impact.

## Open Questions

- None blocking apply. Optional consecutive-legs helper: implement only if a clear one-liner extract exists without new behavior.
