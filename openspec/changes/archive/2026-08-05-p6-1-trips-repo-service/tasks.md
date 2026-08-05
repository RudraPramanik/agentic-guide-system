## 1. Exceptions and schemas

- [x] 1.1 Implement `src/trips/exceptions.py`: `TripNotFoundError`, `TripForbiddenError`, `TripAlreadyClaimedError` (409 / `trip_already_claimed`)
- [x] 1.2 Implement `src/trips/schemas.py`: `TripOut` / `TripPlaceOut` with timing + `polyline` + joined `lat`/`lng` (via `to_shape`); no invented columns

## 2. ORM relationships (no migration)

- [x] 2.1 Add `Trip.places` → `TripPlace` and `TripPlace.place` → `Place` relationships (ordered by day/order); no new columns / no Alembic revision
- [x] 2.2 Confirm model modules still import cleanly

## 3. Repository

- [x] 3.1 Implement `TripRepository(BaseRepository[Trip, UUID])` with flush-only writes
- [x] 3.2 Add `list_by_user(user_id, params)` and `list_by_session(session_id, params)` (soft-delete aware pagination)
- [x] 3.3 Add `get_with_places(trip_id)` with selectinload of places + Place; return `None` if missing/soft-deleted

## 4. TripService

- [x] 4.1 Implement `save_from_state(state, user_id, session_id) -> Trip | None` with locked field map (`leg_polyline` → `polyline`), status COMPLETE/FAILED/DRAFT, commit on success / rollback on failure
- [x] 4.2 Skip persist (`None`) for empty schedule / clarification-only unusable state
- [x] 4.3 Implement `assert_can_access` (guest session match; auth owner or pre-claim guest session) → `TripForbiddenError` on miss
- [x] 4.4 Implement `claim_for_user` (session match + unclaimed → set `user_id` + commit; else 403/409)
- [x] 4.5 Ensure `TripService` never imports or calls `PlannerService`

## 5. Validation and tests

- [x] 5.1 Run step 6.1 import-surface check: `TripRepository` / `TripService` with `save_from_state` + `claim_for_user`
- [x] 5.2 Add focused `tests/trips/` covering save→`get_with_places` polyline, forced mid-insert rollback (zero committed trips), claim success / wrong session 403 / already-claimed 409
- [x] 5.3 Run `python -m pytest tests/trips/ -v` (and full suite if cheap) — green before context stamp

## 6. Context and guards

- [x] 6.1 Update `docs/context.md`: Progress 6.1 ✅, Next → P6.2; list trips exceptions/schemas/repo/service as real; keep trips router + planner HTTP as stubs
- [x] 6.2 Do not register trips/planner HTTP routes; do not touch Redis/SSE; do not mark P6 complete
