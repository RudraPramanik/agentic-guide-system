## 1. Config

- [x] 1.1 Add `NOMINATIM_BASE_URL` and `OVERPASS_API_URL` to `src/config.py` (defaults per step 2.1) and document both in `.env.example`

## 2. Geo schemas

- [x] 2.1 Replace stub `src/geo/schemas.py` with `GeocodedPlace`, `RawPOI`, and `RouteResult` Pydantic models per step 2.1 (no SQLAlchemy/FastAPI imports)

## 3. Geocoder gateway

- [x] 3.1 Replace stub `src/geo/geocoder.py` with Nominatim gateway: `_normalize`, `_throttle`, `_fetch_nominatim` (tenacity 3×, connect/timeout only), `_parse_result`, `geocode` (dict cache + locks, cache misses including `None`), `cache_stats`, `_clear_cache_for_tests` — no `@lru_cache` on async
- [x] 3.2 Confirm `geo/` uses only `get_settings()` for env and never raises httpx exceptions from `geocode` to callers

## 4. CLI script

- [x] 4.1 Create `scripts/test_geocoder.py` (`python scripts/test_geocoder.py "Darjeeling"`)

## 5. Validation (step 2.1)

- [x] 5.1 Live geocode: `python scripts/test_geocoder.py "Darjeeling"` → approximate `GeocodedPlace(name='Darjeeling', lat=27.041, lng=88.263)`
- [x] 5.2 Cache hit check (step 2.1 snippet): clear cache, geocode twice, assert `cache_stats()['hits'] >= 1` and print PASS
- [x] 5.3 Failure path: mock `_fetch_nominatim` with `httpx.ConnectError` → `geocode` returns `None` (no raise)
- [x] 5.4 Async cache correctness: three sequential awaits on same query after first success — no `RuntimeError`

## 6. Context checkpoint

- [x] 6.1 Update `docs/context.md` — mark 2.1 ✅, Next step **2.2**, add `geo/schemas` + `geo/geocoder` to Implemented modules, remove those from stubs, note per-process cache/throttle P6 Redis TODO
