## 1. Preconditions

- [x] 1.1 Confirm Postgres up (`docker compose up -d`) and `DATABASE_URL` points at `:5433`
- [x] 1.2 Confirm `.env` has a **real** `NOMINATIM_USER_AGENT` (contact email) — not a placeholder; do **not** edit `alembic/env.py` (Destination already imported; no migration for this step)

## 2. Step 2.6a — schemas + exceptions

- [x] 2.1 Replace stub `src/destinations/schemas.py` with `DestinationOut`, `DestinationSearchQuery`, `DestinationReadinessOut` per `docs/steps/step2.md` §2.6a (no model/repo/geo imports)
- [x] 2.2 Replace stub `src/destinations/exceptions.py` with `DestinationNotFoundError(NotFoundError)` per step
- [x] 2.3 Run step 2.6a validation (`python -c` import + `status_code == 404` assert)

## 3. Step 2.6b — repository

- [x] 3.1 Implement `DestinationRepository` with `get_by_osm_place_id`, `search_by_name` (ILIKE name/display_name, order place_count desc then name, limit), and atomic `upsert_from_geocoded` (`ON CONFLICT osm_place_id`, counters excluded from SET, `.returning(Destination)`, flush only) — mirror `PlaceRepository` style
- [x] 3.2 Run atomic upsert failure-path validation from step 2.6b (double upsert same `osm_place_id`, same id, no IntegrityError; rollback)

## 4. Step 2.6b — service

- [x] 4.1 Implement `DestinationService.search` cache-aside (DB hit → return; miss → `geocode` → None raises `DestinationNotFoundError`; else upsert + commit + refresh → `[dest]`); import `geocode` only in service
- [x] 4.2 Implement `get_by_id` raising `DestinationNotFoundError` when missing (wrap/check — do not leak only generic `NotFoundError`)
- [x] 4.3 Run step 2.6b happy-path validation (`search('Darjeeling')` then second search same id)

## 5. Context checkpoint

- [x] 5.1 Update `docs/context.md`: Last updated, Next step → **2.4**, mark 2.6a+2.6b ✅, add destinations schemas/exceptions/repository/service to Implemented modules, shrink Stubs list accordingly
