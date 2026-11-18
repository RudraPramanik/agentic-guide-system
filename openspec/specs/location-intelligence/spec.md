## Purpose

Deterministic location candidates, resolution, and search areas for a later planner hook. Generate and the destinations HTTP API stay on their current behavior.

## Requirements

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

### Requirement: Candidate search is a pure merge of supplied hits
Given the same geocoder hits and the same catalog rows, candidate normalization MUST return the same candidates. The merge MUST NOT insert, update, or delete a destination. The result MUST contain at most 10 candidates. Two hits with the same `osm_place_id` MUST become one candidate. Otherwise two hits with the same normalized name (strip, collapse whitespace, lowercase) whose coordinates are within 1 km MUST become one candidate. A merged candidate that has an OSM id MUST use provider `nominatim` and MUST keep a catalog id when a catalog row joined it. A catalog-only candidate MUST use provider `catalog`.

#### Scenario: The same fixture yields the same candidates
- **WHEN** candidate normalization runs twice on one geocoder hit and one catalog row
- **THEN** the two results are equal

#### Scenario: Duplicate OSM ids collapse
- **WHEN** a geocoder hit and a catalog row share one `osm_place_id`
- **THEN** the result contains one candidate, provider `nominatim`, and that catalog id

#### Scenario: Search does not write the catalog
- **WHEN** candidate search runs with a catalog read
- **THEN** no destination upsert runs

### Requirement: Location type comes from existing geocoder fields
Classification MUST use only `addresstype`, `osm_class`, `osm_type_tag`, bbox, and the existing city-scale and oversized checks. It MUST NOT call the network. The first matching rule wins:

- `country` → `country`
- `state`, `region`, `province`, `county`, `state_district`, `continent` → `region`
- `city`, `town`, `village`, `municipality` → `city`
- `suburb`, `neighbourhood`, `neighborhood`, `quarter`, `borough`, `city_district`, `hamlet` → `neighborhood`
- `osm_class` `natural` and type `peak`, `volcano`, `ridge`, or `cliff` → `landmark`
- `osm_class` `tourism` and type `attraction` or `viewpoint` → `landmark`
- `osm_class` `historic`, `amenity`, or `building`, or type `monastery`, `place_of_worship`, `museum`, `memorial`, or `ruins` → `poi`
- `house`, `isolated_dwelling`, or `address` → `address`
- otherwise a city-scale hit that is not oversized → `city`
- otherwise → `poi`

Each candidate MUST include canonical name, location type, lat, lng, country code (two letters or null), admin area (the second comma-separated piece of `display_name`, or null), provider, provider id, confidence, bounding box `[west, south, east, north]` or null, optional catalog id, and a stable explanation that names the rule.

#### Scenario: Darjeeling classifies as a city
- **WHEN** the only hit is named Darjeeling with `addresstype` `city`
- **THEN** the candidate location type is `city`

#### Scenario: Tiger Hill classifies as a landmark
- **WHEN** the only hit is named Tiger Hill with `osm_class` `natural` and `osm_type_tag` `peak`
- **THEN** the candidate location type is `landmark`

#### Scenario: Ghoom Monastery classifies as a POI
- **WHEN** the only hit is named Ghoom Monastery with `osm_class` `historic` and `osm_type_tag` `monastery`
- **THEN** the candidate location type is `poi`

### Requirement: Auto-resolve requires exactly one candidate at or above the confidence threshold
Confidence MUST start from the type prior: `city` `0.92`, `neighborhood` `0.88`, `landmark` `0.86`, `poi` `0.84`, `address` `0.80`, `country` `0.70`, `region` `0.70`. A catalog row with the same `osm_place_id` adds `0.05`, capped at `0.97`. Otherwise a catalog row with the same normalized name within 1 km adds `0.04`, capped at `0.97`. Candidates MUST be ordered by confidence descending, then canonical name ascending.

Resolution status MUST be `resolved` only when the number of candidates whose confidence is greater than or equal to `LOCATION_AUTO_RESOLVE_CONFIDENCE` is exactly one. That candidate is `selected`, and `requires_confirmation` is false. When candidates exist and that count is not exactly one, status MUST be `ambiguous`, `selected` MUST be null, `requires_confirmation` MUST be true, and the candidates MUST still be returned. When there are no candidates, status MUST be `not_found`, `selected` MUST be null, `requires_confirmation` MUST be false, and the reason MUST say the result is empty. A low-confidence hit MUST NOT be replaced with a city center.

#### Scenario: One city clears the threshold
- **WHEN** the only candidate is a city at confidence `0.92` and the threshold is `0.90`
- **THEN** status is `resolved`, that candidate is selected, and confirmation is not required

#### Scenario: A landmark below the threshold asks for confirmation
- **WHEN** the only candidate is a landmark at confidence `0.86` and the threshold is `0.90`
- **THEN** status is `ambiguous`, nothing is selected, confirmation is required, and the landmark remains in the candidate list

#### Scenario: Two cities above the threshold stay ambiguous
- **WHEN** two candidates are each at or above the threshold
- **THEN** status is `ambiguous`, nothing is selected, and both candidates are returned

#### Scenario: No hits are not found
- **WHEN** the geocoder hit list and the catalog row list are both empty
- **THEN** status is `not_found` and nothing is selected

### Requirement: Geocoder timeout and policy errors stay distinct
The live search MUST bound the existing geocoder call with `SEARCH_GEOCODE_TIMEOUT_SECONDS`. On timeout it MUST return `not_found` with reason `geocoder_timeout`. It MUST NOT substitute a city. When the geocoder raises the existing external-service error used for Nominatim 403 and 429, that error MUST propagate. The library MUST NOT report that failure as `not_found`.

#### Scenario: Timeout is an empty resolution
- **WHEN** the geocoder call exceeds `SEARCH_GEOCODE_TIMEOUT_SECONDS`
- **THEN** the resolution is `not_found` with reason `geocoder_timeout`

#### Scenario: A policy rejection is not an empty resolution
- **WHEN** the geocoder raises the external-service error for HTTP 403 or 429
- **THEN** the caller receives that error and no `not_found` resolution is returned

### Requirement: Search area follows the type policy and discloses fallback
City with a bbox MUST use strategy `city_boundary`, a closed rectangular boundary of that bbox, null radius, and `fallback_used` false. City without a bbox MUST use strategy `radius`, radius `LOCATION_CITY_FALLBACK_RADIUS_KM`, and `fallback_used` true, and the description MUST state that radius. Neighborhood with a bbox MUST use strategy `admin_boundary` and `fallback_used` false. Neighborhood without a bbox MUST use strategy `radius`, radius `LOCATION_NEIGHBORHOOD_RADIUS_KM`, and `fallback_used` true. Landmark and POI MUST use strategy `radius`, radius `LOCATION_POI_RADIUS_KM`, and `fallback_used` false. Address MUST use strategy `radius` and radius `LOCATION_NEIGHBORHOOD_RADIUS_KM`, with `fallback_used` false, and the description MUST state that this is the local radius. A map pin with a radius at or below `LOCATION_MAX_RADIUS_KM` MUST use that radius and `fallback_used` false. A map pin radius above the max MUST be clamped to the max, the description MUST state the clamp, and `fallback_used` MUST stay false. A map pin with no radius MUST use `LOCATION_POI_RADIUS_KM` and `fallback_used` true. Country and region MUST be refused with a named oversized-admin error and MUST NOT produce a radius.

#### Scenario: A city boundary is not a landmark radius
- **WHEN** a city candidate has a bbox and a landmark candidate does not
- **THEN** the city area uses `city_boundary` with `fallback_used` false, and the landmark area uses a 10 km radius with `fallback_used` false

#### Scenario: A city missing a boundary discloses the fallback
- **WHEN** a city candidate has no bbox and the city fallback is 15 km
- **THEN** the area uses strategy `radius`, radius 15, and `fallback_used` true

#### Scenario: A map pin cannot exceed the server max
- **WHEN** a map pin requests a radius of 80 km and the max is 50 km
- **THEN** the area radius is 50 and the description states the clamp

#### Scenario: A country does not become a radius
- **WHEN** the anchor location type is `country` or `region`
- **THEN** search-area construction fails with an oversized-admin error and returns no area

### Requirement: Supplied polygons are checked for shape, not topology
A supplied polygon MUST be a GeoJSON `Polygon` or `MultiPolygon`. Each ring MUST have at least four positions and the first position MUST equal the last. Latitude MUST be in `[-90, 90]` and longitude in `[-180, 180]`. Any other geometry type, an open ring, or an out-of-range coordinate MUST be a named rejection and MUST NOT fall back to a radius. Self-intersection MUST NOT be required for acceptance. A valid polygon MUST use strategy `polygon`, store that geometry, and set `fallback_used` false.

#### Scenario: A closed rectangle is accepted
- **WHEN** the input is a closed GeoJSON polygon whose coordinates are in range
- **THEN** the area strategy is `polygon` and `fallback_used` is false

#### Scenario: An open ring is rejected
- **WHEN** a ring's first position differs from its last
- **THEN** construction fails with a named polygon error and no radius area is returned
