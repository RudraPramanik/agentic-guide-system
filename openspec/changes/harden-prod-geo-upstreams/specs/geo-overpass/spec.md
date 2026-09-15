## MODIFIED Requirements

### Requirement: Encapsulated OverpassQL and HTTP contract
`_post_overpass` MUST POST to `OVERPASS_API_URL` with form field `data=<OverpassQL>` and explicit `httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=5.0)` (amended from step `read=30` so Darjeeling-sized queries can complete). The query MUST match the locked step 2.2 template: tourism nodes/ways matching `attraction|viewpoint|museum|monastery`, leisure=park nodes, highway=trailhead nodes, `around` radius in meters (`radius_km * 1000`), `out center tags`. Requests MUST send `User-Agent` from `NOMINATIM_USER_AGENT` and `Accept: application/json` (no new settings key for these headers).

#### Scenario: Radius converted to meters
- **WHEN** `fetch_pois` is called with `radius_km=30`
- **THEN** the OverpassQL `around` clause uses 30000 meters

#### Scenario: JSON Accept header present
- **WHEN** `_post_overpass` issues the HTTP POST
- **THEN** the request includes header `Accept` with value `application/json` and `User-Agent` from settings
