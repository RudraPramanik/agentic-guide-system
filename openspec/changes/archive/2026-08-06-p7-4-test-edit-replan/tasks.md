## 1. Setup + fixtures

- [x] 1.1 Read `AGENT.md`, `docs/context.md`, and `docs/steps/step7.md` §7.4 before coding
- [x] 1.2 Create `tests/trips/test_edit_replan.py` with shared seed helpers (owned multi-stop / multi-day trips, FakeRoutingProvider injection, TripEditEvent count helper); reuse patterns from `test_trip_edit_ops.py` / `test_trip_edit_http.py`
- [x] 1.3 Ensure module never constructs live OSRM or calls LLM; Fake + mocked limiter only

## 2. Service-level happy + failure matrix

- [x] 2.1 Reorder — `order_in_day` matches client; times + `TripPlace.polyline` updated
- [x] 2.2 Reorder preserves order with morning-only category mid-list (preserve-order)
- [x] 2.3 `remove_stop` — stop gone; remaining re-routed
- [x] 2.4 Remove last stop — 422 `day_would_be_empty`; trip unchanged
- [x] 2.5 Remove place not on day — 404 `stop_not_found_on_day`
- [x] 2.6 `add_stop` — new TripPlace; polyline populated
- [x] 2.7 Add duplicate — 409; add wrong destination — 422
- [x] 2.8 Add / reoptimize that forces `dropped_stops` — 422 `edit_would_drop_other_stops`; zero place changes
- [x] 2.9 `reoptimize_day` success with Fake; OSRM-fallback (None polyline) → success no 500
- [x] 2.10 Reorder morning-slot-only → 200 + warnings + commit; remove/add/reoptimize morning errors → still 422
- [x] 2.11 Reorder duplicate ids → 422
- [x] 2.12 Successful edit → exactly one `TripEditEvent`; validation failure → rollback, event count unchanged
- [x] 2.13 Multi-day spy: RoutingProvider calls only for mutated day

## 3. Thin HTTP + gates

- [x] 3.1 Ownership — wrong user → 403 (HTTP); rate limit — mock limiter → 429 on over-quota
- [x] 3.2 Run `python -m pytest tests/trips/test_edit_replan.py -v` → green
- [x] 3.3 Run `python -m pytest tests/ -v` → green (244 passed)
- [x] 3.4 If a scenario fails against locked behavior: fix minimal product bug (or amend `docs/steps/step7.md` first) — do not weaken assertions
  - Fixed `_persist_day_and_audit`: use `repo.delete_trip_place` (SQL) instead of ORM `session.delete` which was resurrected by `Trip.places` cascade delete-orphan; expire `places` before reload

## 4. Context checkpoint

- [x] 4.1 Update `docs/context.md`: Last updated, Progress 7.4 ✅, Next → 7.5, Current state note (full edit/replan pytest), stubs note (7.4 suite landed; 7.5 evaluation polish still pending)
- [x] 4.2 Do not implement 7.5 evaluation polish or 7.6 smoke in this change
