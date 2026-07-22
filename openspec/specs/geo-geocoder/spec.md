## Purpose

Nominatim geocoding gateway and shared geo DTOs (`GeocodedPlace`, `RawPOI`, `RouteResult`) under `src/geo/`.

## Requirements

### Requirement: Geo DTOs for external gateways
The system SHALL define Pydantic models in `src/geo/schemas.py`: `GeocodedPlace` (Nominatim result), `RawPOI` (Overpass element; used by step 2.2), and `RouteResult` (OSRM result; used by step 2.5). The `geo/` package MUST NOT import SQLAlchemy or FastAPI.

#### Scenario: GeocodedPlace fields
- **WHEN** a successful Nominatim payload is parsed
- **THEN** the result is a `GeocodedPlace` with `name`, `lat`, `lng`, `osm_place_id` (`osm_type/osm_id`), `country`, and `display_name`

### Requirement: Config for Nominatim and Overpass base URLs
Settings via `get_settings()` SHALL expose `NOMINATIM_BASE_URL` (default `https://nominatim.openstreetmap.org`) and `OVERPASS_API_URL` (default `https://overpass-api.de/api/interpreter`). `.env.example` MUST document both. Existing `NOMINATIM_USER_AGENT` remains the User-Agent for Nominatim requests.

#### Scenario: Settings readable
- **WHEN** application settings are loaded
- **THEN** `NOMINATIM_BASE_URL` and `OVERPASS_API_URL` are available without reading `os.environ` directly in geo code

### Requirement: Nominatim geocoding gateway
The system SHALL geocode place names only through `src/geo/geocoder.py` (`geocode(query) -> GeocodedPlace | None`). Outbound HTTP MUST use explicit `httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)`, send `User-Agent` from `NOMINATIM_USER_AGENT`, and retry with tenacity (3 attempts, exponential wait 1–8s) only on `httpx.TimeoutException` and `httpx.ConnectError`. On 4xx, exhausted retries, empty results, or other failure, `geocode` MUST return `None` and MUST NOT raise httpx exceptions to callers.

#### Scenario: Successful geocode
- **WHEN** `geocode("Darjeeling")` is called with Nominatim available
- **THEN** a `GeocodedPlace` is returned with approximate lat≈27.041 and lng≈88.263

#### Scenario: Network failure returns None
- **WHEN** the Nominatim fetch fails with `httpx.ConnectError` after retries
- **THEN** `geocode` returns `None` and does not raise to the caller

### Requirement: Process-local async-safe geocode cache
`geocode` MUST use a module-level `dict[str, GeocodedPlace | None]` guarded by `asyncio.Lock`, keyed by a normalized query (strip, collapse whitespace, lowercase). Cache entries MUST store the resolved value (including confirmed `None` misses), never a coroutine or Task. The implementation MUST NOT use `@functools.lru_cache` on the async `geocode` function. Helpers `cache_stats()` and `_clear_cache_for_tests()` MUST exist for validation. Cache and 1 req/sec throttle are per-process (known P2 limitation; Redis deferred to P6).

#### Scenario: Second call is a cache hit
- **WHEN** `geocode("Darjeeling")` is awaited twice sequentially after a cache clear
- **THEN** both awaits succeed with the same lat/lng and `cache_stats()["hits"]` is at least 1

#### Scenario: Repeated awaits do not raise RuntimeError
- **WHEN** the same query is awaited three times after the first successful geocode
- **THEN** all three awaits return a non-None `GeocodedPlace` without raising

### Requirement: Nominatim one-request-per-second throttle
Before each outbound Nominatim call (cache miss path), the geocoder MUST enforce a process-local 1 request/sec throttle via `asyncio.Lock` and `time.monotonic()` so consecutive outbound calls are spaced at least 1.0 second apart within the process.

#### Scenario: Throttle serializes outbound calls
- **WHEN** two distinct uncached queries trigger outbound Nominatim requests in the same process
- **THEN** the second outbound request does not start until at least ~1 second after the first
