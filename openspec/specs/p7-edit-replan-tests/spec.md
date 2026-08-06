## Purpose

P7.4 edit/replan pytest contract: `tests/trips/test_edit_replan.py` covers the locked scenario matrix with FakeRoutingProvider (no live OSRM/LLM).

## Requirements

### Requirement: Full P7 edit/replan pytest suite

The project SHALL provide `tests/trips/test_edit_replan.py` that proves P7 day-edit behavior with `FakeRoutingProvider` (no live OSRM or LLM). Prefer service-level calls for semantics; use thin HTTP for ownership and rate-limit cases. The suite MUST cover at least these scenarios from `docs/steps/step7.md` §7.4:

1. Reorder — `order_in_day` matches client; times + `TripPlace.polyline` updated
2. Reorder preserves order with morning-only category mid-list (preserve-order)
3. `remove_stop` — stop gone; remaining re-routed
4. Remove last stop — 422 `day_would_be_empty`; trip unchanged
5. Remove place not on day — 404 `stop_not_found_on_day`
6. `add_stop` — new TripPlace; polyline populated
7. Add duplicate — 409
8. Add wrong destination — 422
9. Add that forces `dropped_stops` — 422 `edit_would_drop_other_stops`; zero place changes
10. `reoptimize_day` — success with Fake
11. Reoptimize that forces drop — same 422 as add
12. Ownership — wrong user → 403
13. OSRM fallback — None polyline → success (no 500)
14. Reorder morning-slot-only validate → 200 + warnings + commit
15. Remove/add/reoptimize morning-slot errors → still 422 (no downgrade)
16. Reorder duplicate ids → 422
17. Successful edit → exactly one `TripEditEvent` (not 0 or 2)
18. Validation failure → rollback; `TripEditEvent` count unchanged
19. Spy: `RoutingProvider` calls only for mutated day on multi-day trip
20. Rate limit — mock limiter → 429 on over-quota

DB MUST use `wandr_test` / existing trips fixtures. The module MUST NOT require live OSRM or LLM.

#### Scenario: Edit/replan pytest module is green

- **WHEN** a developer runs `python -m pytest tests/trips/test_edit_replan.py -v` after implementation
- **THEN** the twenty locked scenarios above are covered and pass

#### Scenario: Failed add leaves audit count unchanged

- **WHEN** an add that forces `dropped_stops` (or other validation failure) is exercised
- **THEN** the test asserts rollback — `TripEditEvent` count is unchanged and TripPlaces match pre-edit

#### Scenario: Suite stays offline

- **WHEN** CI runs `test_edit_replan.py` without network OSRM/LLM
- **THEN** all tests pass using FakeRoutingProvider and mocked rate limiter as needed

### Requirement: Full trips suite remains green

After adding `test_edit_replan.py`, `python -m pytest tests/ -v` MUST remain green. Existing `test_trip_edit_ops.py` / `test_trip_edit_http.py` MAY remain; they MUST NOT be weakened to skip ownership, rollback, or v2.1 regression cases.

#### Scenario: Full pytest gate

- **WHEN** `python -m pytest tests/ -v` runs with `wandr_test` available
- **THEN** all tests pass before claiming step 7.4 complete
