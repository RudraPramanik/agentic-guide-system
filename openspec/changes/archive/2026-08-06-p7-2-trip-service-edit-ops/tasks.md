## 1. Preserve-order schedule + morning-slot prefix

- [x] 1.1 Read `AGENT.md`, `docs/context.md`, and `docs/steps/step7.md` §7.2 before coding
- [x] 1.2 Extend `build_day_schedule(..., *, preserve_order: bool = False)` in `src/travel_engine/schedule_builder.py` — when True, skip `_extract_morning_first`; keep lunch/duration/leg rules; default False unchanged
- [x] 1.3 Prefix `check_morning_slots` errors with `morning_slot_violation: ` in `src/travel_engine/trip_validator.py` (string-only; other rules untouched)
- [x] 1.4 Add/extend Fake tests: preserve-order keeps morning-only in slot 3; default path still morning-extracts; prefixed morning error exists

## 2. Trip edit exceptions, schemas, repository

- [x] 2.1 Add `TripEditValidationError`, `TripStopConflictError`, `TripStopNotFoundError` to `src/trips/exceptions.py`
- [x] 2.2 Add `ReorderStopsIn` / `AddStopIn` to `src/trips/schemas.py` (no routes)
- [x] 2.3 Extend `TripRepository` with flush-only helpers: hard-delete TripPlace by (trip_id, place_id, day), update day stop fields, sole `insert_edit_event`

## 3. Evaluation thin hook

- [x] 3.1 Add `EvaluationService.mark_trip_edited(trip_id)` — flag-only / no-op-safe; never writes `TripEditEvent`; missing evaluation does not raise
- [x] 3.2 Add flush-only repo helper for setting `user_edited=True` on latest evaluation when present (or document intentional no-op if deferred to 7.5)

## 4. TripService day surgery

- [x] 4.1 Wire RoutingProvider DI on `TripService` (constructor default `OsrmRoutingProvider()`, per-call `routing=` override); comment last-write-wins concurrency
- [x] 4.2 Implement private helpers: `_hydrate_scored`, `_snapshot_day`, `_fixed_order_day` (matrix + consecutive legs + `populate_leg_polylines` only — no `optimize_route`), `_optimize_day`, `_schedule_mutated_day`, `_validate_full_trip` (unchanged days from stored fields; REORDER morning downgrade), `_persist_day_and_audit` (zip `leg_polylines` → `TripPlace.polyline`; TripEditEvent; `mark_trip_edited`; single commit)
- [x] 4.3 Implement `reorder_stops` — exact permutation check; preserve-order schedule; `EditType.REORDER`
- [x] 4.4 Implement `remove_stop` — 404 not-on-day; 422 `day_would_be_empty`; optimize + drop guard; `EditType.REMOVE_STOP`
- [x] 4.5 Implement `add_stop` — Place 404 / wrong dest 422 / duplicate 409; optimize + drop guard; `EditType.ADD_STOP`
- [x] 4.6 Implement `reoptimize_day` — optimize + drop guard; `EditType.REOPTIMIZE_DAY`
- [x] 4.7 Grep: no PlannerService / `execute_tool` / LLM / duplicate polyline loops; no invented DayPlan/ScheduledStop polyline fields; no FastAPI edit routes

## 5. Service Fake tests + close out

- [x] 5.1 Unit/Fake: reorder preserves order + polylines on TripPlace; one `TripEditEvent`
- [x] 5.2 Unit/Fake: remove last → error; add duplicate → 409; add that would drop → 422 with zero TripPlace/edit-event mutation
- [x] 5.3 Run `python -m pytest tests/travel_engine/ tests/trips/ -v` green (or targeted suites covering new tests)
- [x] 5.4 Update `docs/context.md`: mark 7.2 ✅, Next → 7.3, note edit methods + preserve-order schedule in implemented modules / stubs
- [x] 5.5 Do not implement 7.3 HTTP routes or rate limit in this change
