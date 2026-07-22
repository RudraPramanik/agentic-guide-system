## Purpose

Overpass API POI scraper gateway under `src/geo/overpass.py` (`fetch_pois` → `RawPOI`).

## Requirements

### Requirement: Overpass POI scraping gateway
The system SHALL fetch points of interest only through `src/geo/overpass.py` via `fetch_pois(lat, lng, radius_km) -> list[RawPOI]`. Callers MUST NOT construct OverpassQL or call Overpass outside `src/geo/`. The module MUST NOT import SQLAlchemy, FastAPI, or database session code. URL MUST come from `get_settings().OVERPASS_API_URL` (already configured in step 2.1).

#### Scenario: Live Darjeeling scrape returns POIs
- **WHEN** `fetch_pois(27.041, 88.263, 30)` is called with Overpass available
- **THEN** a non-empty `list[RawPOI]` is returned with at least 50 items for the Darjeeling area

#### Scenario: Public entry point only
- **WHEN** application or seed code needs Overpass POIs
- **THEN** it calls `fetch_pois` and does not build OverpassQL or POST to Overpass itself

### Requirement: Encapsulated OverpassQL and HTTP contract
`_post_overpass` MUST POST to `OVERPASS_API_URL` with form field `data=<OverpassQL>` and explicit `httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)` (amended from step `read=30` so Darjeeling-sized queries can complete). The query MUST match the locked step 2.2 template: tourism nodes/ways matching `attraction|viewpoint|museum|monastery`, leisure=park nodes, highway=trailhead nodes, `around` radius in meters (`radius_km * 1000`), `out center tags`. Requests SHOULD send `User-Agent` from `NOMINATIM_USER_AGENT` (no new settings key).

#### Scenario: Radius converted to meters
- **WHEN** `fetch_pois` is called with `radius_km=30`
- **THEN** the OverpassQL `around` clause uses 30000 meters

### Requirement: Element parsing to RawPOI
`_element_to_poi` MUST map Overpass elements to `RawPOI` using: `osm_id = "{type}/{id}"`; `name` from tags; lat/lng from element lat/lon or `center` for ways; `category` from `_category_from_tags`; `raw_tags` as a copy of tags. Elements without a name tag MUST be skipped. Elements without usable coordinates MUST be skipped.

#### Scenario: Named node becomes RawPOI
- **WHEN** an element has `type=node`, `id=12345`, tags including `name` and `tourism=museum`, and lat/lon
- **THEN** the result is `RawPOI` with `osm_id="node/12345"`, that name, those coordinates, `category="museum"`, and `raw_tags` populated

#### Scenario: Unnamed elements discarded
- **WHEN** an element has no `name` tag
- **THEN** it is not included in the returned list

### Requirement: Locked category mapping
`_category_from_tags` MUST apply priority-ordered mapping: `tourism=museum` → `museum`; `tourism=viewpoint` → `viewpoint`; `tourism=monastery` → `monastery`; `tourism=attraction` → `attraction`; `leisure=park` → `park`; `highway=trailhead` → `trailhead`; otherwise `attraction`.

#### Scenario: Viewpoint takes tourism match
- **WHEN** tags include `tourism=viewpoint`
- **THEN** category is `viewpoint`

#### Scenario: Unknown tags fall back to attraction
- **WHEN** tags match none of the locked OSM key/value pairs
- **THEN** category is `attraction`

### Requirement: Deduplicate by osm_id
`fetch_pois` MUST deduplicate parsed POIs by `osm_id` before returning, with last occurrence winning when duplicates appear in the Overpass response.

#### Scenario: Duplicate osm_id keeps last
- **WHEN** `_post_overpass` returns two elements that parse to the same `osm_id`
- **THEN** the returned list contains one entry for that `osm_id`, equal to the last parsed `RawPOI`

### Requirement: Overpass resilience and empty-list failure boundary
Outbound Overpass calls MUST retry with tenacity (3 attempts, exponential wait 2–16s) on `httpx.TimeoutException`, `httpx.ConnectError`, and transient 5xx `httpx.HTTPStatusError` (public Overpass often returns 504). HTTP timeouts MUST use `httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)` (amended from step `read=30` so Darjeeling-sized queries can complete). On HTTP 4xx, `_post_overpass` MUST log a warning and return `{"elements": []}`. After exhausted retries or any other HTTP/network failure, `fetch_pois` MUST return `[]` and MUST NOT raise httpx exceptions to callers. The gateway MUST NOT abort callers or write to the database.

#### Scenario: ConnectError after retries returns empty list
- **WHEN** `_post_overpass` raises `httpx.ConnectError` (including when mocked for validation)
- **THEN** `fetch_pois` returns `[]` and does not raise to the caller

#### Scenario: Client error yields empty elements then empty list
- **WHEN** Overpass responds with HTTP 4xx
- **THEN** `_post_overpass` returns `{"elements": []}` and `fetch_pois` returns `[]`
