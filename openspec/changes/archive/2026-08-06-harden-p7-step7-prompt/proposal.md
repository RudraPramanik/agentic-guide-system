## Why

`docs/steps/step7.md` is the P7 implementation SoT, but the v1 contract has an internal contradiction on who creates `TripEditEvent`, ambiguous locks (permutation, stop-not-found, “recompute lightly”), and silent product risks (optimize drop-retry on add, polyline loss on persist). Critic review plus codebase verification produced a hardened v2.1 contract: keep accepted critic fixes, correct flawed solutions (shared-helper legs API, DayPlan polyline fields), and lock the reorder vs morning-extract conflict that neither draft resolved. Update `step7.md` now so code applies do not invent behavior.

## What Changes

- **Replace** `docs/steps/step7.md` with hardened **v2.1** Cursor build contract (single SoT for P7 implementation).
- Resolve **TripEditEvent ownership**: `TripService`/`TripRepository` creates the event; `EvaluationService.mark_trip_edited(trip_id)` only sets `user_edited` (flag-only; blueprint `record_edit` naming treated as delta).
- Lock **no silent drops**: non-empty `optimize_route.dropped_stops` on add/reoptimize → 422 `edit_would_drop_other_stops` + rollback.
- Lock **unchanged days**: reconstruct from stored `TripPlace` fields only — zero extra routing calls.
- Lock **geometry sharing** without regressing `optimize_route`: promote/reuse polyline population; keep `OptimizeResult.legs` as **full pairwise matrix**; reorder uses shared polyline helper + consecutive chain for fixed order.
- Lock **polyline persist path**: carry `leg_polylines` parallel to schedule result → write `TripPlace.polyline` at persist — **do not** invent `ScheduledStop.leg_polyline` / `DayPlan.day_polyline`.
- Lock **reorder order preservation**: REORDER uses a **preserve-order** timing path (no `_extract_morning_first`); morning-slot violations on reorder downgrade to warnings; other edit types keep hard errors.
- Lock precise permutation check, `stop_not_found_on_day` 404, user-keyed edit rate limit dependency, concurrency as documented MVP last-write-wins.
- Expand prompt substeps to **7.0–7.6** (shared geometry extract as 7.1; renumber service/router/tests/eval/ship).
- Refresh OpenSpec delta specs to match v2.1 locks (supersede intent of `design-p7-edit-replan` for the build contract).
- **Non-goals:** implementing P7 application code in this change (docs + specs only); chat full-trip replan; evaluation HTTP; row-level locking; new packages; changing generation-time morning extract for non-reorder paths.

## Capabilities

### New Capabilities
- `p7-trip-edit-replan`: Hardened day-scoped edit HTTP + TripService day surgery (travel_engine + RoutingProvider only), audit, validation/drop/polyline/reorder locks, user-keyed rate limit.
- `p7-edit-evaluation`: `EvaluationService.mark_trip_edited` flag-only; TripService owns `TripEditEvent` creation in the same UoW.
- `p7-step7-build-contract`: Requirements that `docs/steps/step7.md` is the non-empty v2.1 canonical P7 Cursor build contract (7.0–7.6).

### Modified Capabilities
- `trips-repository-service`: `save_from_state` persists `base_lat`/`base_lng` in preferences; edit surface + `_resolve_base`.
- `travel-engine-route-optimizer`: Shared geometry/polyline helper for fixed-order callers without collapsing `OptimizeResult.legs` to consecutive-only.
- `travel-engine-schedule-builder`: Preserve-order schedule entry point for P7 reorder (generation path unchanged).

## Impact

- **Docs (this change):** `docs/steps/step7.md` rewritten as v2.1 SoT; `docs/step7_critics.md` remains historical review notes (not the build contract).
- **Prior planning:** `design-p7-edit-replan` artifacts are superseded for implementation guidance by this change’s `step7.md` + specs; archive/sync later as usual.
- **Code (future apply batches only):** `src/trips/*`, `src/travel_engine/route_optimizer.py`, `src/travel_engine/schedule_builder.py`, `src/evaluation/*`, config rate-limit settings, `tests/trips/test_edit_replan.py`; optional smoke + `docs/context.md` on final ship step.
- **AGENT.md:** Router→Service→Repository; travel_engine purity; evaluation notified on every edit; no LLM/planner tools on edit path.
- **Blueprint delta (documented, not silently conflicting):** evaluation no longer *creates* `TripEditEvent`; DELETE does not call `build_route` tool; reorder preserve-order + morning-slot warning downgrade.
