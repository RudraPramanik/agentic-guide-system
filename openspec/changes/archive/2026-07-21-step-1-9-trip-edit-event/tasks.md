## 1. Model

- [x] 1.1 Add `EditType` enum and `TripEditEvent` to `src/trips/models.py` per `docs/steps/step1.md` Step 1.9 (imports, FKs, index, docstring, `__repr__`)
- [x] 1.2 Verify import: `python -c "from src.trips.models import TripEditEvent, EditType; print(list(EditType))"`

## 2. Alembic

- [x] 2.1 Update `alembic/env.py` — import `TripEditEvent` from `src.trips.models`
- [x] 2.2 Generate migration: `alembic revision --autogenerate -m "add_trip_edit_events"`
- [x] 2.3 Review generated file: `trip_edit_events` present; `edit_type` enum; FKs CASCADE/SET NULL; composite index; **no changes to existing 6 tables**
- [x] 2.4 Apply: `alembic upgrade head`

## 3. Validation (from step1.md)

- [x] 3.1 `\dt` — 7 tables including `trip_edit_events`
- [x] 3.2 `\d trip_edit_events` — all columns: id, trip_id, edit_type, day_number, place_id, payload, created_at, updated_at
- [x] 3.3 `SELECT typname FROM pg_type WHERE typname = 'edit_type'` — one row

## 4. Wrap-up

- [x] 4.1 Run `pytest tests/ -v` — no regressions
- [x] 4.2 Update `docs/context.md`: Last updated, Next step **1.10**, mark 1.9 ✅, add `TripEditEvent`/`EditType` to Implemented modules
