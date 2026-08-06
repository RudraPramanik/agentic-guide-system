## Why

P7.1 shipped the shared `populate_leg_polylines` helper; the next build-contract step is **7.2** (`docs/steps/step7.md`): day surgery on persisted trips. Without TripService edit ops + a preserve-order schedule path, reorder would either TSP-permute the user’s order or morning-extract would defeat their permutation — both forbidden by the v2.1 locks. Blueprint product intent (P7 Edit & Replan table + Service Layer / UoW / CoR validation) is delivered here at the **service** layer; HTTP routes stay in 7.3.

## What Changes

- Extend `schedule_builder` with a **preserve-order** entry (`preserve_order=True` flag or dedicated function) that skips `_extract_morning_first`; default morning-extract stays for generation and non-reorder edits.
- Optionally prefix morning-slot validator errors with `morning_slot_violation:` so REORDER can downgrade those errors to warnings.
- Add trip edit exceptions (`TripEditValidationError` 422, `TripStopConflictError` 409, `TripStopNotFoundError` 404) and input schemas (`ReorderStopsIn`, `AddStopIn`).
- Extend `TripRepository` with flush-only helpers for day mutations + sole `TripEditEvent` insert (TripPlace hard-delete).
- Implement `TripService` day surgery: `reorder_stops`, `remove_stop`, `add_stop`, `reoptimize_day` — hydrate → travel_engine + injected `RoutingProvider` → `validate_trip` → single-commit UoW (TripPlaces + `TripEditEvent` + `mark_trip_edited`).
- Thin `EvaluationService.mark_trip_edited` (flag-only / no-op-safe) so the UoW can call the final name; full evaluation lookup may land in 7.5.
- Unit/Fake tests proving reorder preserves order + polylines, remove-last / duplicate-add / drop-forcing failures leave the trip unchanged.
- Update `docs/context.md` after validation (Next → 7.3).

**Non-goals:** FastAPI edit routes / rate limit (7.3); full edit pytest suite (7.4); full `mark_trip_edited` evaluation linkage polish (7.5); smoke/docs cadence (7.6); PlannerService / `execute_tool` / LLM on edit path; cross-day move; new packages/migrations; inventing `ScheduledStop.leg_polyline` / `DayPlan.day_polyline`.

**Naming note:** Blueprint labels service edit ops as “7.1” and HTTP as “7.2”; `docs/steps/step7.md` v2.1 expands P7 to **7.0–7.6** with this work as **7.2**. Build from the step contract; product behavior follows the blueprint table with intentional deltas locked in step7 (TripService owns `TripEditEvent`; edits call travel_engine + `RoutingProvider`, not TOOL_REGISTRY; reorder uses preserve-order schedule).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `travel-engine-schedule-builder`: Fulfill the preserve-order scheduling requirement — implement the API; keep default morning-extract unchanged.
- `travel-engine-trip-validator`: Optionally prefix morning-slot error strings with `morning_slot_violation:` (string-only, backward compatible) for TripService REORDER downgrade filtering.
- `trips-repository-service`: Expand the day-edit surface into the full 7.2 contract — exceptions, schemas, repo flush helpers, private day-surgery helpers, four public methods, UoW + audit ownership, Fake-backed tests (no HTTP).
- `p7-edit-evaluation`: Land a thin callable `mark_trip_edited` (flag-only; missing evaluation MUST NOT fail the edit) so TripService can invoke it in-UoW before 7.5 polish.

## Impact

- **Code:** `src/travel_engine/schedule_builder.py`, optionally `trip_validator.py`; `src/trips/exceptions.py`, `schemas.py`, `repository.py`, `service.py`; thin `src/evaluation/service.py` (+ repo helper if needed); `tests/travel_engine/` + `tests/trips/` Fake unit coverage.
- **AGENT.md:** Router→Service→Repository (no routes yet); travel_engine purity; no LLM/planner on edit; evaluation records every edit (event via TripService; flag via EvaluationService).
- **Blueprint patterns:** Service Layer, Unit of Work, Strategy/`RoutingProvider` DI, Chain of Responsibility (`validate_trip`), Configuration Object (`travel_rules`).
- **Depends on:** P7.0 `_resolve_base` / base prefs; P7.1 `populate_leg_polylines` (legs stay full pairwise).
- **Unlocks:** 7.3 four HTTP edit endpoints + user-keyed rate limit.
- **No DB migration / no new packages / no live endpoint changes in this step.**
