## Context

P7.0–7.1 are done: trips persist `base_lat`/`base_lng` via `_resolve_base`, and `populate_leg_polylines` is public while `OptimizeResult.legs` stays full pairwise. Step **7.2** (`docs/steps/step7.md`) implements day surgery on `TripService` before HTTP (7.3).

Blueprint (`docs/blueprint_final.md` v6.1) product surface is four day-scoped edits with ownership, validation rollback, and audit. Step7 v2.1 is the build contract and locks intentional deltas vs older blueprint wording: TripService owns `TripEditEvent`; edits call `travel_engine` + `RoutingProvider` (not TOOL_REGISTRY / `build_route`); reorder uses preserve-order schedule.

Today: `build_day_schedule` always morning-extracts; `TripService` has save/ownership/claim/GeoJSON only; no edit exceptions/schemas; `TripRepository` has no edit-event insert; `EvaluationService.mark_trip_edited` is missing.

Constraints: AGENT.md layering; travel_engine purity; no new packages; no routes in this step; OSRM only via injected `OsrmRoutingProvider` (fail-soft already).

## Goals / Non-Goals

**Goals:**

- Preserve-order schedule API; default morning-extract unchanged.
- Optional `morning_slot_violation:` error-string prefix for REORDER downgrade.
- Four public `TripService` edit methods with Fake-testable day surgery + UoW.
- Exactly one `TripEditEvent` per successful edit (TripRepository sole writer) + `mark_trip_edited` flag call.
- Polylines only via `populate_leg_polylines` → zip onto `TripPlace.polyline`.

**Non-Goals:**

- HTTP routes / rate limit (7.3)
- Full `tests/trips/test_edit_replan.py` matrix (7.4) — 7.2 ships focused Fake unit coverage only
- Full evaluation polish beyond thin callable stub (7.5)
- Cross-day moves, chat replan, LLM, PlannerService, row locking

## Decisions

1. **Preserve-order via `preserve_order: bool = False` on `build_day_schedule`**
   - **Choice:** Add keyword-only flag; when True, skip `_extract_morning_first` and time the given order. Keep a thin alias `build_day_schedule_preserve_order` only if call-site clarity needs it.
   - **Why:** Single timing implementation; generation callers unchanged; matches step7 “either” option with least API surface.
   - **Alternatives:** Separate function that duplicates lunch/timing — rejected (drift risk).

2. **Fixed-order day lives on TripService (`_fixed_order_day`)**
   - **Choice:** `travel_matrix` once → consecutive `RouteLeg` chain for that order → `populate_leg_polylines`. MUST NOT call `optimize_route` / MUST NOT permute.
   - **Why:** Critics lock #4/#17; 7.1 deferred consecutive-legs helper to 7.2; service owns the fixed-order orchestration.
   - **Alternatives:** Module helper in `route_optimizer` — acceptable if trivial, but TripService ownership is enough for this step.

3. **Routing DI: constructor default `OsrmRoutingProvider()`, optional `routing=` per call**
   - **Choice:** `TripService.__init__(session, routing=None)` stores default provider; public edit methods accept `*, routing=None` override for Fake tests.
   - **Why:** Blueprint Strategy/Protocol DI; tests inject Fake without monkeypatching geo.
   - **Alternatives:** Always require explicit routing — noisier for future router wiring.

4. **Validate full trip; unchanged days from stored TripPlace fields only**
   - **Choice:** `_validate_full_trip` builds `TripItinerary` with mutated day from new plan; other days’ `total_travel_min` = sum of stored `travel_time_min`, stops rebuilt from DB fields — **zero** RoutingProvider calls for unchanged days.
   - **Why:** Lock #20; CoR validator still sees whole trip.
   - **Alternatives:** Re-route all days — rejected (cost + accidental multi-day OSRM).

5. **REORDER morning-slot downgrade in TripService only**
   - **Choice:** After `validate_trip`, if `edit_type == REORDER`, move errors matching `morning_slot_violation*` (or equivalent morning-slot substring if prefix deferred) into warnings; remaining errors → `TripEditValidationError`.
   - **Why:** Lock #21; validator stays pure/generic; reorder is the only soft path.
   - **Alternatives:** Soften validator itself — rejected (would weaken generation VALIDATE).

6. **Non-empty `dropped_stops` → 422 before persist**
   - **Choice:** On remove/add/reoptimize, if `optimize_route` returns non-empty `dropped_stops` → `TripEditValidationError` code `edit_would_drop_other_stops` with details; no TripPlace mutation. Still-over-budget single stop with empty drops fails via travel-cap validate → 422 (not only via drops).
   - **Why:** Lock #19; silent drop is worse than rejecting the edit.

7. **UoW ownership: TripService creates `TripEditEvent`; evaluation flag-only**
   - **Choice:** `_persist_day_and_audit`: mutate TripPlaces → `TripRepository.insert_edit_event` → `EvaluationService.mark_trip_edited` → `commit` → `get_with_places`. On any validation/business failure before commit: rollback; zero edit events.
   - **Why:** Lock #16; blueprint “record edit” intent without EvaluationService owning the audit row.
   - **Alternatives:** Evaluation creates event (blueprint 7.4 wording) — rejected by step7 SoT.

8. **Thin `mark_trip_edited` now**
   - **Choice:** Implement callable method that flush-sets `user_edited=True` on latest evaluation if present, else no-op. Prefer real lookup if a one-liner repo helper is easy; otherwise safe no-op stub that 7.5 hardens.
   - **Why:** Step prefers calling the final name even if thin; edit path must not 500 on missing evaluation.

9. **Concurrency comment only**
   - **Choice:** Document last-write-wins on `TripService`; no `SELECT FOR UPDATE` in P7.
   - **Why:** Lock #22 MVP.

10. **Schemas without routes**
    - **Choice:** Add `ReorderStopsIn` / `AddStopIn` now so 7.3 imports them; unused by HTTP until then.
    - **Why:** Step 7.2 explicitly extends schemas.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Morning-extract accidentally used on reorder | Spec + Fake test: morning-only mid-list stays mid-list; assert `preserve_order=True` call path |
| Half-updated day committed | Single commit after validate; raise before mutate-or-rollback on failure |
| Duplicate polyline loops | Only `populate_leg_polylines`; ban local OSRM/geometry loops in review |
| Anchor check fails after hydrate `score=1.0` | Hydration uses score=1.0 (> `ANCHOR_MIN_SCORE`); document if fixture scores differ |
| `mark_trip_edited` stub hides missing flag | 7.5 task + scenario; 7.2 at least must not raise / must not write TripEditEvent |
| Blueprint numbering confusion (7.1 vs 7.2) | Follow step7.md; comment in context.md Next → 7.3 |
| Inventing DayPlan/ScheduledStop polyline fields | Zip `leg_polylines` parallel to schedule at persist only |

## Migration Plan

- No Alembic migration; `TripEditEvent` / `EditType` already exist (P1.9).
- Deploy = ship code; rollback = revert service/schedule/eval commits; no data backfill.
- Existing generation path unchanged (`preserve_order` default False).

## Open Questions

- None blocking. Prefer `preserve_order` kwflag over a second public function unless apply discovers awkward call sites.
- Prefixing validator strings is optional per step; include if REORDER filter is cleaner than substring-matching existing prose.
