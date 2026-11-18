## MODIFIED Requirements

### Requirement: Location settings exist and default to legacy values
Settings loaded through `get_settings()` MUST expose `LOCATION_V2_ENABLED` (default `false`), `LOCATION_AUTO_RESOLVE_CONFIDENCE` (default `0.90`), `LOCATION_POI_RADIUS_KM` (default `10`), `LOCATION_NEIGHBORHOOD_RADIUS_KM` (default `5`), `LOCATION_CITY_FALLBACK_RADIUS_KM` (default `15`), and `LOCATION_MAX_RADIUS_KM` (default `50`). `.env.example` MUST document each name and default. `src/travel_engine/**` MUST NOT read `LOCATION_V2_ENABLED` and MUST NOT import `src.location_intelligence`. `src/planner/**` MAY read `LOCATION_V2_ENABLED` and MAY import `src.location_intelligence`. While the flag is false, generate MUST NOT call the library.

#### Scenario: Defaults when the environment omits the knobs
- **WHEN** settings load with none of those variables set
- **THEN** the six values equal the defaults above

#### Scenario: Generate and the engine ignore the flag
- **WHEN** `LOCATION_V2_ENABLED` is false and Python files under `src/travel_engine/` are scanned
- **THEN** those engine files do not mention `LOCATION_V2_ENABLED` or import `src.location_intelligence`, and generate does not call the location library

#### Scenario: The engine still ignores the flag when it is true
- **WHEN** Python files under `src/travel_engine/` are scanned while the flag is true
- **THEN** none of them mention `LOCATION_V2_ENABLED` or import `src.location_intelligence`

#### Scenario: Generate does not call the library while the flag is false
- **WHEN** `LOCATION_V2_ENABLED` is false and a client posts `POST /api/v1/planner/generate`
- **THEN** the location library is not called

## ADDED Requirements

### Requirement: A point is inside a search area or it is dropped
A radius area MUST contain a point only when the haversine distance from the anchor is less than or equal to `radius_km`. A `city_boundary`, `admin_boundary`, or `polygon` area MUST contain a point only when it lies in the stored GeoJSON rings. A point outside that geometry MUST be outside even when it lies inside a covering circle used to query the database. The check MUST NOT use a fixed 30 km radius.

#### Scenario: A landmark radius excludes a far point
- **WHEN** the area is a 10 km radius and a point is more than 10 km from the anchor
- **THEN** the point is outside the area

#### Scenario: A bbox ring excludes a point outside the rectangle
- **WHEN** the area is a closed city-boundary rectangle and a point lies outside that ring
- **THEN** the point is outside the area

### Requirement: Map pins use a user provider and are not merged from the geocoder
Candidate merge MUST still emit only provider `nominatim` or `catalog`. A map pin supplied by the client MUST be represented with provider `user`, location type `map_pin`, and the client latitude and longitude after range checks. It MUST NOT be passed through candidate merge and MUST NOT call the geocoder.

#### Scenario: A dropped pin does not become a geocoder hit
- **WHEN** a map pin is built from a latitude, a longitude, and a radius
- **THEN** the anchor provider is `user`, the location type is `map_pin`, and the geocoder is not called

### Requirement: Location routes exist only while the flag is on
The system MUST expose `POST /api/v1/locations/search`, `POST /api/v1/locations/resolve`, and `POST /api/v1/locations/search-area`. Each success body MUST be `ApiResponse` of the existing resolution object or the existing search-area object. The router MUST call the location service and MUST NOT upsert a destination. Query text MUST be at least 2 and at most 200 characters. No login MUST be required.

While `LOCATION_V2_ENABLED` is false, each route MUST respond HTTP 404 and MUST NOT call the geocoder.

`POST /api/v1/locations/search` MUST accept `{ "query": string }` and MUST return the library resolution for that query.

`POST /api/v1/locations/resolve` MUST accept `query` and optional `provider` plus `provider_id`. Without `provider_id`, the result MUST be the library resolution unchanged. With `provider` and `provider_id`, when that pair is present in the candidate list, status MUST be `resolved`, that candidate MUST be selected, and `requires_confirmation` MUST be false. When that pair is absent, status MUST be `not_found`, nothing MUST be selected, and the reason MUST be `anchor_not_confirmed`.

`POST /api/v1/locations/search-area` MUST build an area from a posted anchor, an optional `radius_km`, and an optional polygon, using the existing search-area policy. It MUST NOT persist a trip. `oversized_admin` and `invalid_polygon` MUST be HTTP 422 with those codes. Latitude outside `[-90, 90]` or longitude outside `[-180, 180]` MUST be HTTP 422 with code `invalid_coordinates`. A nominatim 403 or 429 MUST still propagate as the existing external-service error and MUST NOT be stored as `not_found`.

#### Scenario: Search is closed when the flag is off
- **WHEN** `LOCATION_V2_ENABLED` is false and a client posts `/api/v1/locations/search`
- **THEN** the response is HTTP 404 and the geocoder is not called

#### Scenario: Search returns a resolution and writes no destination
- **WHEN** the flag is true and the query is `Darjeeling`
- **THEN** the success envelope contains a resolution and no destination upsert runs

#### Scenario: Resolve confirms the posted candidate only
- **WHEN** resolve is called with a provider and provider id that appear in the candidate list
- **THEN** status is `resolved`, that candidate is selected, and confirmation is not required

#### Scenario: Resolve does not substitute a different candidate
- **WHEN** resolve is called with a provider id that is not in the candidate list
- **THEN** status is `not_found`, nothing is selected, and the reason is `anchor_not_confirmed`

#### Scenario: Search-area clamps a map pin and does not save a trip
- **WHEN** the flag is true and the body is a map pin with radius 80 km while the max is 50 km
- **THEN** the area radius is 50, the description states the clamp, and no trip row is written

#### Scenario: A country is not given a radius
- **WHEN** search-area is asked to build an area for location type `country` or `region`
- **THEN** the response is HTTP 422 with code `oversized_admin` and no area is returned
