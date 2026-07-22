## Why

P2.3 is done (`PlaceRepository`), but destinations remain stubs — seed (2.4) and `GET /destinations/search` (2.6c) both need atomic destination upsert + cache-aside search. Steps **2.6a + 2.6b** are next per `docs/context.md` and the locked canonical order in `docs/steps/step2.md`.

## What Changes

- Replace stub `src/destinations/schemas.py` with Pydantic DTOs (`DestinationOut`, `DestinationSearchQuery`, `DestinationReadinessOut`)
- Replace stub `src/destinations/exceptions.py` with `DestinationNotFoundError` (404 via `NotFoundError`)
- Replace stub `src/destinations/repository.py` with `DestinationRepository` — `search_by_name`, `get_by_osm_place_id`, atomic `upsert_from_geocoded` (`ON CONFLICT osm_place_id`, counters excluded from SET)
- Replace stub `src/destinations/service.py` with `DestinationService` — cache-aside `search()` (DB → geocode → upsert → commit) and `get_by_id()` raising `DestinationNotFoundError`
- Validate with step 2.6a/2.6b scripts; update `docs/context.md` (2.6a+2.6b ✅, Next → 2.4)
- **No step2.md rewrite required** — plan is implementable; design records small clarifications (error wrapping, env checklist, alembic unchanged)

## Capabilities

### New Capabilities

- `destinations-core`: Destination schemas/exceptions + repository atomic upsert + service cache-aside search (no HTTP router yet)

### Modified Capabilities

- *(none — no main-spec requirement delta; router/rate-limit land in 2.6c / 2.6c′)*

## Impact

- **Code:** `src/destinations/schemas.py`, `exceptions.py`, `repository.py`, `service.py` only (models already real from P1.4a)
- **Deps:** none new — uses existing `geo.geocode`, `GeocodedPlace`, `BaseRepository`, `get_settings()`
- **Env:** no new vars for this step; runtime needs `DATABASE_URL` + working `NOMINATIM_USER_AGENT` (see design)
- **Alembic:** **no change** — `Destination` already imported in `alembic/env.py`; table exists (migration 002); do **not** put API keys in Alembic
- **AGENT.md:** Service may call `geo.geocode`; repository never HTTP; repository flush-only; service commits on Nominatim-miss path (AuthService pattern)
- **Non-goals:** destinations router (2.6c), path rate limit (2.6c′), seed script (2.4), places service/router (2.7), OSRM (2.5), readiness scoring impl (2.8), pytest suite (2.9)
