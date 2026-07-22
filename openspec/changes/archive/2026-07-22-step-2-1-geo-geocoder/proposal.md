## Why

P1 is complete; P2 starts with the Nominatim geocoding gateway so destination search and seed can resolve city names without calling external APIs outside `src/geo/`. Step 2.1 in `docs/steps/step2.md` delivers geo schemas, config URLs, and a correctness-fixed async cache (no `@lru_cache` on `async def`).

## What Changes

- Implement **step 2.1 only** — replace stub `src/geo/schemas.py` and `src/geo/geocoder.py` with real modules
- Add `NOMINATIM_BASE_URL` and `OVERPASS_API_URL` to `src/config.py` and `.env.example`
- Define shared geo DTOs: `GeocodedPlace`, `RawPOI` (for 2.2), `RouteResult` (for 2.5)
- Implement Nominatim gateway: explicit httpx timeouts, tenacity retry (connect/timeout only), process-local dict cache + 1 req/sec throttle, failure returns `None`
- Add `scripts/test_geocoder.py` CLI for live validation
- Expose `cache_stats()` / `_clear_cache_for_tests()` for cache-hit assertions

## Capabilities

### New Capabilities

- `geo-geocoder`: Nominatim geocoding gateway + geo Pydantic schemas (`GeocodedPlace`, `RawPOI`, `RouteResult`) with resilience contract and safe async cache

### Modified Capabilities

- (none)

## Impact

- **Code:** `src/geo/schemas.py`, `src/geo/geocoder.py` (stubs → real), `src/config.py`, `.env.example`, `scripts/test_geocoder.py` (new)
- **Deps:** none — `httpx` and `tenacity` already in `requirements.txt`
- **APIs:** no new HTTP routes
- **AGENT.md:** geo only via `src/geo/`; all env via `get_settings()`; no SQLAlchemy/FastAPI in `geo/`; no new packages
- **Docs:** update `docs/context.md` after validation (Next step → 2.2); note per-process cache/throttle limitation (P6 Redis follow-up)
- **Non-goals:** Overpass (2.2), place repository (2.3), OSRM (2.5), destinations/places routers, seed script, pytest suite (2.9)
