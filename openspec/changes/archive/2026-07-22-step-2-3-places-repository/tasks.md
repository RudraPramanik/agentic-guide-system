## 1. Implement PlaceRepository

- [x] 1.1 Replace stub `src/places/repository.py` with `PlaceRepository(BaseRepository[Place, uuid.UUID])` — imports per step 2.3 (`Geography`, `ST_*`, `insert`, `RawPOI`, `PageParams`)
- [x] 1.2 Implement `upsert_from_poi` — single `insert(Place).on_conflict_do_update(index_elements=[Place.osm_id], ...).returning(Place)`; map `poi.raw_tags` → `tags`; `ST_MakePoint(poi.lng, poi.lat)`; no commit; return RETURNING row (no second SELECT)
- [x] 1.3 Implement `find_within_radius` — soft-delete filter + `ST_DWithin(cast(location, Geography), cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), Geography), radius_km * 1000)` + `limit`
- [x] 1.4 Implement `list_by_destination` — delegate to `list_paginated(filters={"destination_id": destination_id}, params=params)`
- [x] 1.5 Implement `count_by_destination` — COUNT non-deleted places for `destination_id`

## 2. Validate

- [x] 2.1 Run step 2.3 happy-path validation (`python -c` upsert idempotency + nearby/far radius + `list_by_destination` + `to_shape` lat check; Postgres up, then rollback)
- [x] 2.2 Run step 2.3 concurrent-style upsert validation (two repos, same `osm_id`, no IntegrityError, same id)

## 3. Context checkpoint

- [x] 3.1 Update `docs/context.md`: Last updated, Next step → **2.6a**, Progress 2.3 ✅, Implemented modules row for `PlaceRepository`, remove places/repository from stubs-only implication
