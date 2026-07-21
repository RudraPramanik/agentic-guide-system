## ADDED Requirements

### Requirement: Geocoding gateway

The system SHALL geocode place names via `src/geo/geocoder.py` with tenacity retry, explicit httpx timeouts, and LRU cache. After retries exhausted it SHALL return `None`.

#### Scenario: Successful geocode

- **WHEN** `geocode("Darjeeling")` is called with network available
- **THEN** a `GeocodedPlace` with lat/lng is returned

### Requirement: POI scraping gateway

The system SHALL fetch POIs via `src/geo/overpass.py` with resilience contract; on failure return empty list.

#### Scenario: Overpass returns POIs

- **WHEN** Overpass query runs for a seeded coordinate and radius
- **THEN** a list of `RawPOI` with osm_id and category is returned

### Requirement: OSRM routing gateway

The system SHALL compute routes via `src/geo/osrm.py` with haversine × 1.4 fallback when OSRM fails.

#### Scenario: OSRM unavailable

- **WHEN** OSRM endpoint is unreachable after retries
- **THEN** `RouteResult` is returned using straight-line fallback and a warning is logged

### Requirement: Destination search API

The system SHALL expose `GET /api/v1/destinations/search?q=` using DB-first cache-aside with Nominatim fallback.

#### Scenario: Second search hits cache

- **WHEN** the same destination query is searched twice
- **THEN** the second response is served from DB without external geocode log

### Requirement: Places list API

The system SHALL expose paginated `GET /api/v1/places?destination_id=` returning `PaginatedResponse[PlaceOut]`.

#### Scenario: Paginated places

- **WHEN** a seeded destination has 144 places and page=2 size=10 is requested
- **THEN** response includes total, pages, has_next=true

### Requirement: Seed destination script

The system SHALL provide `scripts/seed_destination.py` that geocodes, scrapes Overpass, and upserts places idempotently.

#### Scenario: Seed Darjeeling

- **WHEN** `python scripts/seed_destination.py --destination "Darjeeling"` completes
- **THEN** places and destination rows exist in Postgres
