## MODIFIED Requirements

### Requirement: PlanRequest schema for generate
The system MUST provide `PlanRequest` in `src/planner/schemas.py` with fields:
`destination_id: UUID`, `raw_input: str`, optional `days: int | None`, optional `base_lat` / `base_lng: float | None`, optional `accommodation_label: str | None` (display-only), optional `discovery_anchor`, and optional `radius_km: float | None`.

`discovery_anchor`, when present, MUST carry `canonical_name`, `location_type`, `lat`, `lng`, and `provider` (`nominatim`, `catalog`, or `user`), and MAY carry `query` and `provider_id`. `base_lat` and `base_lng` MUST remain the trip base. They MUST NOT be overwritten from `discovery_anchor`.

A body that omits `discovery_anchor` and `radius_km` MUST still be accepted.

#### Scenario: Schema accepts blueprint PlanRequest fields
- **WHEN** a valid JSON body includes `destination_id`, `raw_input`, and optional `days`, `base_lat`, `base_lng`, `accommodation_label`
- **THEN** FastAPI/Pydantic accepts the body as `PlanRequest`

#### Scenario: An anchor does not replace the trip base
- **WHEN** a body sets `base_lat` and `base_lng` and also sets `discovery_anchor` to a different point
- **THEN** the accepted trip base is the body's `base_lat` and `base_lng`

## ADDED Requirements

### Requirement: Flag-off generate ignores the anchor
While `LOCATION_V2_ENABLED` is false, generate MUST ignore `discovery_anchor` and `radius_km`. The idempotency material and the preference-cache key MUST be the same string they are today for the same destination, text, days, and base. The graph state MUST NOT carry a search area. SSE event names MUST stay the same, and `itinerary_done` MUST NOT gain an anchor field.

#### Scenario: A legacy body is unchanged with the flag off
- **WHEN** the flag is false and the body has no anchor
- **THEN** generate follows the current destination and base path and does not call the location library

#### Scenario: A posted anchor is ignored with the flag off
- **WHEN** the flag is false and the body includes `discovery_anchor` and `radius_km`
- **THEN** the idempotency material matches the material for that body with those fields omitted, and no search area is stored

### Requirement: Flag-on generate builds one server-owned search area
While `LOCATION_V2_ENABLED` is true, generate MUST build one search area before the graph and MUST pass that area into retrieval. The area stored on the trip MUST be this server-built area. A client polygon MUST NOT be stored.

When `discovery_anchor` is absent, the anchor MUST be the destination center with location type `city` and provider `catalog`, and the area MUST be the disclosed city fallback of `LOCATION_CITY_FALLBACK_RADIUS_KM` with `fallback_used` true. Generate MUST NOT geocode that destination again and MUST NOT use a 30 km radius.

When `provider` is `user` and `location_type` is `map_pin`, generate MUST NOT call the geocoder. The radius MUST be the posted `radius_km` after clamping to `LOCATION_MAX_RADIUS_KM`, or `LOCATION_POI_RADIUS_KM` with `fallback_used` true when `radius_km` is omitted.

When `provider` is `nominatim` or `catalog`, generate MUST search `query` when present and `canonical_name` otherwise, and MUST select only the candidate with that provider and provider id. If that candidate is missing, generate MUST fail HTTP 422 with code `anchor_not_confirmed` before the graph and MUST NOT select another candidate. If the confirmed type is `country` or `region`, generate MUST fail HTTP 422 with code `oversized_admin` before the graph and MUST NOT start an LLM call. Latitude or longitude out of range MUST be HTTP 422 with code `invalid_coordinates` before the graph.

A confirmed city or neighborhood that has a boundary MUST keep that boundary. A posted `radius_km` MUST NOT replace it. A confirmed radius strategy MUST use a posted `radius_km` after the same clamp. The description MUST state a clamp when one happens.

Omitted `base_lat` and `base_lng` MUST still default to the destination center. When the flag is true and an anchor or a radius is present, the idempotency material and the preference-cache key MUST include that anchor identity and radius so two areas do not share a cached trip. When both are absent, those strings MUST match the legacy material for the same destination, text, days, and base.

SSE event names MUST stay the same. The anchor MUST be readable from the saved trip, not from a new `itinerary_done` field.

#### Scenario: A destination-only body uses the disclosed city fallback
- **WHEN** the flag is true and the body has a destination id and no discovery anchor
- **THEN** the stored search area uses strategy `radius`, the city fallback radius, and `fallback_used` true, and the radius is not 30

#### Scenario: A map pin does not move the trip base
- **WHEN** the flag is true, `base_lat` and `base_lng` are the destination center, and the anchor is a map pin elsewhere
- **THEN** retrieval is constrained to the pin area and the stored trip base remains the destination center

#### Scenario: An unconfirmed candidate does not start the graph
- **WHEN** the flag is true and the posted provider id is not in the fresh candidate list
- **THEN** the response is HTTP 422 with code `anchor_not_confirmed` and no planner graph runs

#### Scenario: A country anchor does not start the graph
- **WHEN** the confirmed location type is `country` or `region`
- **THEN** the response is HTTP 422 with code `oversized_admin` and no LLM call runs

#### Scenario: Two radii do not share a cache entry
- **WHEN** the flag is true and two bodies differ only in `radius_km`
- **THEN** they do not resolve to the same preference-cache entry
