## MODIFIED Requirements

### Requirement: Encapsulated OverpassQL and HTTP contract

`_post_overpass` MUST POST to `OVERPASS_API_URL` with form field `data=<OverpassQL>` and explicit `httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)`. The query MUST request named POIs within `around` radius in meters (`radius_km * 1000`) using `out center tags`, and MUST include at least:

- tourism nodes/ways matching `attraction|viewpoint|museum|monastery` (existing)
- leisure=park and highway=trailhead (existing)
- amenity nodes matching `cafe|restaurant`
- amenity nodes matching `place_of_worship`
- historic nodes/ways with a name
- natural nodes matching `peak|waterfall`

Requests SHOULD send `User-Agent` from `NOMINATIM_USER_AGENT` (no new settings key for User-Agent). Callers outside `src/geo/` MUST still not construct OverpassQL.

#### Scenario: Radius converted to meters

- **WHEN** `fetch_pois` is called with `radius_km=30`
- **THEN** the OverpassQL `around` clause uses 30000 meters

#### Scenario: Cafe amenity is queried

- **WHEN** the OverpassQL template is inspected or executed
- **THEN** it includes an `amenity` selector covering `cafe` (and `restaurant`)

#### Scenario: Historic and nature selectors present

- **WHEN** the OverpassQL template is inspected
- **THEN** it includes historic and natural (`peak|waterfall`) selectors in addition to the original tourism/park/trailhead set

### Requirement: Locked category mapping

`_category_from_tags` MUST apply priority-ordered mapping that covers at least: `tourism=museum` → `museum`; `tourism=viewpoint` → `viewpoint`; `tourism=monastery` → `monastery`; `tourism=attraction` → `attraction`; `leisure=park` → `park`; `highway=trailhead` → `trailhead`; `amenity=cafe` → `cafe`; `amenity=restaurant` → `restaurant`; `amenity=place_of_worship` → `temple`; historic=* → `historic`; `natural=peak|waterfall` → `nature`; otherwise `attraction`.

#### Scenario: Viewpoint takes tourism match

- **WHEN** tags include `tourism=viewpoint`
- **THEN** category is `viewpoint`

#### Scenario: Cafe maps to cafe

- **WHEN** tags include `amenity=cafe`
- **THEN** category is `cafe`

#### Scenario: Place of worship maps to temple

- **WHEN** tags include `amenity=place_of_worship`
- **THEN** category is `temple`

#### Scenario: Unknown tags fall back to attraction

- **WHEN** tags match none of the locked OSM key/value pairs
- **THEN** category is `attraction`

## ADDED Requirements

### Requirement: Overpass remains callable for OSM-only retrieval

`fetch_pois` MUST remain a public geo-gateway function for Overpass-only scraping. The places-provider facade MAY call `fetch_pois` when `overpass` is enabled. Behavior on failure MUST remain fail-soft `[]` as previously specified.

#### Scenario: Direct fetch_pois still works

- **WHEN** `fetch_pois(lat, lng, radius_km)` is called with Overpass available
- **THEN** a `list[RawPOI]` is returned without requiring OpenTripMap or Geoapify keys
