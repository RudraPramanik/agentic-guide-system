## Purpose

Deterministic location candidates, resolution, and search areas for a later planner hook. Generate and the destinations HTTP API stay on their current behavior.

## ADDED Requirements

### Requirement: Location settings exist and default to legacy values
Settings loaded through `get_settings()` MUST expose `LOCATION_V2_ENABLED` (default `false`), `LOCATION_AUTO_RESOLVE_CONFIDENCE` (default `0.90`), `LOCATION_POI_RADIUS_KM` (default `10`), `LOCATION_NEIGHBORHOOD_RADIUS_KM` (default `5`), `LOCATION_CITY_FALLBACK_RADIUS_KM` (default `15`), and `LOCATION_MAX_RADIUS_KM` (default `50`). `.env.example` MUST document each name and default. `src/planner/**` and `src/travel_engine/**` MUST NOT read `LOCATION_V2_ENABLED`.

#### Scenario: Defaults when the environment omits the knobs
- **WHEN** settings load with none of those variables set
- **THEN** the six values equal the defaults above

#### Scenario: Generate and the engine ignore the flag
- **WHEN** Python files under `src/planner/` and `src/travel_engine/` are scanned
- **THEN** none of them mention `LOCATION_V2_ENABLED` or import `src.location_intelligence`

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
