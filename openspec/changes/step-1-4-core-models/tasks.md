## 1. Step 1.4a — User + Destination

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, `docs/steps/step1.md` §1.4a
- [x] 1.2 Implement `src/auth/models.py` (User)
- [x] 1.3 Implement `src/destinations/models.py` (Destination)
- [x] 1.4 Add User + Destination imports to `alembic/env.py`
- [x] 1.5 Run step 1.4a validation snippet — expect PASS

## 2. Step 1.4b — Place + Trip + TripPlace

- [x] 2.1 Implement `src/places/models.py` (Place with Geometry POINT SRID 4326)
- [x] 2.2 Implement `src/trips/models.py` (TripStatus, Trip, TripPlace — include `Text` import for polyline)
- [x] 2.3 Add Place + Trip imports to `alembic/env.py`
- [x] 2.4 Run step 1.4b validation snippet — expect PASS

## 3. Step 1.4c — TripEvaluation

- [ ] 3.1 Implement `src/evaluation/models.py` (TripEvaluation — all blueprint fields)
- [ ] 3.2 Add TripEvaluation import to `alembic/env.py`
- [ ] 3.3 Run step 1.4c validation snippet — expect PASS

## 4. Alembic prep for 1.4d

- [ ] 4.1 Add `alembic/script.py.mako` (standard Alembic template)
- [ ] 4.2 Add `include_object` filter to `alembic/env.py` (ignore non-metadata tables on autogenerate)
- [ ] 4.3 Confirm all five model import lines present in env.py

## 5. Step 1.4d — Migration 002

- [ ] 5.1 Ensure Docker Postgres up and bare `DATABASE_URL` available
- [ ] 5.2 Run `alembic revision --autogenerate -m "create_all_tables"`
- [ ] 5.3 Review generated migration against step 1.4d checklist (6 tables, Geometry, enum, indexes, no spurious DROPs)
- [ ] 5.4 Run `alembic upgrade head`
- [ ] 5.5 Validate: `\dt` (6 tables), `\di` (indexes), `trip_status` pg_type, `alembic current` shows head

## 6. Context checkpoint

- [ ] 6.1 Update `docs/context.md`: 1.4a–1.4d ✅, next step 1.5, add model modules to Implemented, remove from stubs
