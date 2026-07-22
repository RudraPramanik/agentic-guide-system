## Why

P2.2 delivered Overpass → `RawPOI`, but places cannot be persisted yet — `src/places/repository.py` is still a step-0.1 stub. Step 2.3 is next (`docs/context.md`): seed (2.4) and places APIs depend on an atomic PostGIS upsert, geography radius search, and destination-scoped pagination.

## What Changes

- Replace stub `src/places/repository.py` with real `PlaceRepository` (`BaseRepository[Place, uuid.UUID]`)
- Atomic `upsert_from_poi` via `INSERT ... ON CONFLICT (osm_id) DO UPDATE ... RETURNING` (no check-then-insert, no post-upsert SELECT)
- `find_within_radius` with locked `geography` casts + meter distances (`ST_DWithin`)
- `list_by_destination` / `count_by_destination` for paginated list and seed counters
- Validate with step 2.3 inline scripts (idempotent upsert, radius units, concurrent-style upsert); update `docs/context.md` (2.3 ✅, Next → 2.6a)

**Step-doc readiness:** `docs/steps/step2.md` §2.3 is **good to go without amendment** — v2 already locks geography units, RETURNING upsert, and runnable validation. This change implements that step as written (design clarifications only, no step rewrite).

## Capabilities

### New Capabilities

- `places-repository`: Place persistence — atomic OSM upsert, geography radius query, destination-scoped list/count (flush-only; no HTTP)

### Modified Capabilities

- *(none — no existing main-spec requirement delta; `geo-foundation` roadmap capability stays high-level until later P2 API steps)*

## Impact

- **Code:** `src/places/repository.py` only (models/schemas already exist from P1 / P2.1–2.2)
- **Deps:** none new — `geoalchemy2`, `shapely` already in `requirements.txt`; PostGIS via existing migrations
- **Prereqs:** Place model (`osm_id` unique, `Geometry` POINT 4326, soft-delete), `BaseRepository.list_paginated` / `_soft_delete_filter`, `RawPOI`, Destination for validation fixtures
- **AGENT.md:** Repository never commits; Router→Service→Repository (no router in this step); no geo HTTP outside `src/geo/`
- **Non-goals:** seed script (2.4), destinations repo/service (2.6), places router/service schemas (2.7), OSRM (2.5), pytest `tests/places/` (2.9)
