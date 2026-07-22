## Why

Step 2.1 delivered Nominatim + geo DTOs (`RawPOI` ready). Seed and place upsert need a real Overpass gateway next — `src/geo/overpass.py` is still a step-0.1 stub. Step 2.2 in `docs/steps/step2.md` implements the POI scraper so callers never build OverpassQL or call Overpass outside `src/geo/`.

## What Changes

- Implement **step 2.2 only** — replace stub `src/geo/overpass.py` with the Overpass POI gateway
- Parse Overpass elements into existing `RawPOI` (from 2.1); locked category mapping + unnamed skip + `osm_id` dedupe
- Resilience: explicit httpx timeouts, tenacity 3× (connect/timeout only), failure returns `[]` (never raises to callers)
- Add `scripts/test_overpass.py` CLI for live Darjeeling validation
- No config/schema changes — `OVERPASS_API_URL` and `RawPOI` already landed in 2.1

## Capabilities

### New Capabilities

- `geo-overpass`: Overpass API POI scraper gateway (`fetch_pois`) with OverpassQL encapsulation, category mapping, dedupe, and empty-list failure boundary

### Modified Capabilities

- (none)

## Impact

- **Code:** `src/geo/overpass.py` (stub → real), `scripts/test_overpass.py` (new)
- **Deps:** none — `httpx` and `tenacity` already in `requirements.txt`
- **APIs:** no new HTTP routes
- **AGENT.md:** geo only via `src/geo/`; all env via `get_settings()`; no SQLAlchemy/FastAPI/DB in `geo/`; no new packages
- **Docs:** update `docs/context.md` after validation (Next step → 2.3); remove `geo/overpass.py` from stubs
- **Non-goals:** place repository (2.3), OSRM (2.5), seed script (2.4), destinations/places services, pytest suite files (2.9 `tests/geo/test_overpass.py`), config/schema changes (already done in 2.1)
