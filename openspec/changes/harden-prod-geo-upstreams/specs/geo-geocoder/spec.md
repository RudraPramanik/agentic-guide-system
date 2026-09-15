## MODIFIED Requirements

### Requirement: Config for Nominatim and Overpass base URLs
Settings via `get_settings()` SHALL expose `NOMINATIM_BASE_URL` (default `https://nominatim.openstreetmap.org`) and `OVERPASS_API_URL` (default `https://overpass-api.de/api/interpreter`). Settings SHALL also expose optional `NOMINATIM_API_KEY` (default empty). When `NOMINATIM_API_KEY` is non-empty, Nominatim search requests MUST include it as query parameter `key`. `.env.example` MUST document `NOMINATIM_BASE_URL`, `OVERPASS_API_URL`, `NOMINATIM_USER_AGENT`, and `NOMINATIM_API_KEY`. Existing `NOMINATIM_USER_AGENT` remains the User-Agent for Nominatim requests.

#### Scenario: Settings readable
- **WHEN** application settings are loaded
- **THEN** `NOMINATIM_BASE_URL`, `OVERPASS_API_URL`, and `NOMINATIM_API_KEY` are available without reading `os.environ` directly in geo code

#### Scenario: API key attached when configured
- **WHEN** `NOMINATIM_API_KEY` is non-empty and a Nominatim search request is sent
- **THEN** the request query includes `key` equal to that setting value

### Requirement: Nominatim geocoding gateway
The system SHALL geocode place names only through `src/geo/geocoder.py`. Outbound HTTP MUST use explicit `httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)`, send `User-Agent` from `NOMINATIM_USER_AGENT`, and retry with tenacity (3 attempts, exponential wait 1–8s) only on `httpx.TimeoutException` and `httpx.ConnectError`. On successful HTTP with an empty result list, network exhaustion after retries, or other non-policy failures, `geocode` MUST return `None` and MUST NOT raise httpx exceptions to callers. On Nominatim HTTP 4xx responses that indicate client/policy/rate rejection (including 403 and 429), `geocode` MUST raise `ExternalServiceError` with `service="nominatim"` (and MUST NOT return `None` for that path).

#### Scenario: Successful geocode
- **WHEN** `geocode("Darjeeling")` is called with Nominatim available
- **THEN** a `GeocodedPlace` is returned with approximate lat≈27.041 and lng≈88.263

#### Scenario: Network failure returns None
- **WHEN** the Nominatim fetch fails with `httpx.ConnectError` after retries
- **THEN** `geocode` returns `None` and does not raise to the caller

#### Scenario: Policy rejection raises ExternalServiceError
- **WHEN** Nominatim responds with HTTP 403 (or 429)
- **THEN** `geocode` raises `ExternalServiceError` with details identifying service `nominatim` and does not return `None`

### Requirement: Process-local async-safe geocode cache
`geocode` MUST use a module-level `dict[str, GeocodedPlace | None]` guarded by `asyncio.Lock`, keyed by a normalized query (strip, collapse whitespace, lowercase). Cache entries MUST store the resolved value (including confirmed empty-result `None` misses), never a coroutine or Task. Upstream 4xx policy/rate failures that raise `ExternalServiceError` MUST NOT be written into the process cache. The implementation MUST NOT use `@functools.lru_cache` on the async `geocode` function. Helpers `cache_stats()` and `_clear_cache_for_tests()` MUST exist for validation. Cache and 1 req/sec throttle are per-process (known P2 limitation; Redis deferred to P6).

#### Scenario: Second call is a cache hit
- **WHEN** `geocode("Darjeeling")` is awaited twice sequentially after a cache clear
- **THEN** both awaits succeed with the same lat/lng and `cache_stats()["hits"]` is at least 1

#### Scenario: Repeated awaits do not raise RuntimeError
- **WHEN** the same query is awaited three times after the first successful geocode
- **THEN** all three awaits return a non-None `GeocodedPlace` without raising

#### Scenario: Policy failure is not negatively cached
- **WHEN** Nominatim returns HTTP 403 for a query and a later call uses a fixed configuration that would succeed
- **THEN** the later call is allowed to hit the network again (the 403 outcome was not stored as a cached `None`)
