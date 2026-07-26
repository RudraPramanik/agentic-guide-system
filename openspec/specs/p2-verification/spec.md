## Purpose

P2 verification closeout — deterministic pytest coverage for geo gateways, readiness math, PostGIS persistence, and public HTTP routes, plus the live fail-fast `scripts/test_p2_smoke.py` end-to-end proof and the rule that P2 completion is only recorded after both pass.

## Requirements

### Requirement: P2 geo gateway tests are deterministic
The project SHALL provide pytest coverage for the Nominatim, Overpass, and OSRM gateways. These tests MUST mock outbound boundary helpers and MUST NOT call public network services. Coverage MUST include successful mapping and each named failure fallback, plus geocoder resolved-value caching, Overpass deduplication/query units, and OSRM invalid input.

#### Scenario: Geocoder cache stores successful resolved values
- **WHEN** `geocode` is awaited twice for normalized-equivalent queries after a cache clear and the mocked fetch returns one result
- **THEN** both calls return a `GeocodedPlace`, the fetch helper is called once, and cache hits increase without a reused-coroutine error

#### Scenario: Geocoder caches confirmed misses
- **WHEN** the mocked Nominatim fetch returns an empty result and the same normalized query is geocoded twice
- **THEN** both calls return `None` and the fetch helper is called once

#### Scenario: Geocoder network failure is contained
- **WHEN** the mocked Nominatim boundary raises an `httpx` connection or timeout error
- **THEN** `geocode` returns `None`, no `httpx` exception reaches the caller, and the test allows for tenacity’s up to 3 fetch attempts

#### Scenario: Overpass parsing and deduplication
- **WHEN** the mocked Overpass payload contains named nodes, a way with center coordinates, unnamed elements, and duplicate OSM ids
- **THEN** `fetch_pois` maps categories and coordinates, skips invalid elements, and returns one last-wins item per OSM id

#### Scenario: Overpass radius uses meters
- **WHEN** `fetch_pois` is called with `radius_km=30`
- **THEN** the query passed to the mocked POST boundary contains a 30000-meter radius

#### Scenario: Overpass network failure is contained
- **WHEN** the mocked Overpass boundary raises a retryable HTTP/network error
- **THEN** `fetch_pois` returns an empty list and does not raise

#### Scenario: OSRM success and coordinate order
- **WHEN** `get_route` receives two `(lat, lng)` waypoints and the mocked OSRM response contains distance, duration, and geometry
- **THEN** the result converts meters to kilometers and seconds to minutes, reports `fallback_used=False`, and the OSRM URL construction uses `lng,lat` order

#### Scenario: OSRM miss uses named fallback
- **WHEN** the mocked OSRM boundary returns no usable route or raises
- **THEN** `get_route` returns a positive haversine-derived result with `fallback_used=True`

#### Scenario: OSRM rejects insufficient waypoints
- **WHEN** `get_route` receives fewer than two waypoints
- **THEN** it raises `ValueError` before outbound HTTP is attempted

### Requirement: P2 persistence contracts have database regression coverage
The project SHALL test destination and place repositories against the PostGIS test database. Destination upsert coverage MUST distinguish sequential idempotency from a concurrent race using separate sessions and committed transactions. Place radius coverage MUST prove kilometer inputs are evaluated as geography meters.

#### Scenario: Destination upsert preserves counters
- **WHEN** an existing destination with non-zero counters is upserted again with the same `osm_place_id`
- **THEN** the same destination id is returned and `place_count`, `enriched_count`, and `indexed_count` remain unchanged

#### Scenario: Concurrent destination upserts converge
- **WHEN** two independently created async sessions concurrently upsert the same new `osm_place_id` and each worker commits its own transaction
- **THEN** both workers complete without `IntegrityError`, return the same destination id, and exactly one matching row exists

#### Scenario: Radius search uses kilometer-scale geography
- **WHEN** a place approximately 3 km from a query point is searched with 5 km and 1 km radii
- **THEN** it is included at 5 km and excluded at 1 km

### Requirement: P2 readiness and HTTP contracts have regression coverage
The project SHALL test the pure readiness formula and the public destinations/places routes through the ASGI client. Tests MUST cover response envelopes, pagination, missing-resource errors, destination-specific rate limiting, and P2 `search_available=False` behavior.

#### Scenario: Readiness tiers cover sparse limited and ready inputs
- **WHEN** `compute_readiness` is called with `(0,0,0,False)`, `(144,0,0,False)`, and `(144,100,100,True)`
- **THEN** the results are respectively sparse, limited with score in `[0.35, 0.45]`, and ready with the documented percentages and messages

#### Scenario: Unenriched place_count 50 is sparse not limited
- **WHEN** `compute_readiness(50, 0, 0, False)` is called
- **THEN** `tier == "sparse"` and `score == 0.2`, proving `place_count >= 50` alone is not a limited-band acceptance gate

#### Scenario: Destination routes return expected envelopes
- **WHEN** search and readiness endpoints are called for seeded or mocked successful data
- **THEN** they return successful `ApiResponse` payloads with destination data and P2 readiness values

#### Scenario: Destination search miss is 404
- **WHEN** destination search misses the database and mocked geocoding returns `None`
- **THEN** the endpoint returns 404 with the Wandr not-found error envelope

#### Scenario: Search rate limit is path specific
- **WHEN** a mocked limiter denies only the destinations search key
- **THEN** destinations search returns 429 with limit 20 while health for the same client remains allowed under the default route limit

#### Scenario: Places list is paginated
- **WHEN** an existing destination with places is requested with explicit page and size parameters
- **THEN** the endpoint returns `PaginatedResponse` metadata and only the requested page of `PlaceOut` items

#### Scenario: Unknown destination does not look empty
- **WHEN** places are listed for an unknown destination UUID
- **THEN** the endpoint returns 404 with code `not_found`, not a successful empty page

#### Scenario: Unknown place is 404
- **WHEN** a nonexistent place UUID is requested
- **THEN** the endpoint returns 404

### Requirement: Seed failure boundaries are testable without the development database
The seed script SHALL expose a narrow async pipeline helper that accepts an `AsyncSession`; it SHALL NOT open or commit that session. The CLI wrapper SHALL retain session ownership, commit-on-success behavior, and exit codes. Tests MUST use the test session and mocked geo gateways.

#### Scenario: One POI failure does not abort the batch
- **WHEN** one of three place upserts raises inside its SAVEPOINT
- **THEN** the remaining POIs are attempted and `seed_places` returns a success count of two

#### Scenario: Empty Overpass result still persists destination state
- **WHEN** geocoding succeeds and mocked Overpass returns an empty list
- **THEN** the session-injected pipeline creates or updates the destination, sets `place_count` to zero, and does not treat the result as geocode failure

#### Scenario: CLI geocode failure remains fatal
- **WHEN** the CLI-facing seed wrapper receives no geocoded destination
- **THEN** it returns exit code 1 and does not commit seed data

### Requirement: P2 smoke script provides a fail-fast end-to-end proof
The project SHALL provide `scripts/test_p2_smoke.py` for manual execution against configured live geo services and the development database. It MUST run sections sequentially, print Windows-safe ASCII `[OK]`/`[FAIL]` markers, stop on failure with a non-zero exit code, and finish successful execution with `ALL P2 SMOKE TESTS PASSED`.

#### Scenario: Live P2 happy path
- **WHEN** Docker dependencies and configured Nominatim, Overpass, and OSRM services are available and the smoke script runs for Darjeeling
- **THEN** it verifies geocoder cache hits, at least 50 fetched POIs, persisted seed counters, full `/api/v1/...` search/places/readiness responses, search rate-limit header 20, a positive OSRM-or-fallback route, and geography-radius consistency with `limit >= place_count`

#### Scenario: Readiness limited-band requires formula-true place_count
- **WHEN** the smoke readiness section runs for an unenriched seeded destination
- **THEN** it asserts `tier=limited` and `0.35 <= score <= 0.45` only if `place_count >= 100`; otherwise it fails with the observed place_count rather than treating `>= 50` as sufficient

#### Scenario: Reapplying fetched POIs is idempotent
- **WHEN** the smoke script applies the same already-fetched POI list to the same destination again
- **THEN** the destination id and unique place count remain stable without a second live Overpass request

#### Scenario: External dependency failure is explicit
- **WHEN** a required live geo section cannot satisfy its invariant
- **THEN** the script prints the failed section and observed reason and exits non-zero without printing the success sentinel

### Requirement: P2 completion is recorded only after verification
The project SHALL mark P2.9 and P2.10 complete in `docs/context.md` and set P3.1 as the next step only after focused P2 tests, the full pytest suite, and the P2 smoke script pass. The update MUST preserve the recorded per-process cache/rate-limit limitations and MUST NOT duplicate module or endpoint entries already added for P2.7b/P2.8.

#### Scenario: Verification succeeds
- **WHEN** all P2 pytest and smoke validation commands pass
- **THEN** context records P2 completion, the P2 test/smoke artifacts, and P3.1 as next

#### Scenario: Verification fails
- **WHEN** any required P2 pytest or smoke command fails
- **THEN** context does not claim P2.9/P2.10 completion
