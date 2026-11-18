# canonical-trip-identity Specification

## Purpose
One canonical id space for a saved trip: the same place id on the stop, the map, and a suggestion, with an honest geometry label and a version so two edits cannot silently overwrite each other.

## Requirements

### Requirement: Canonical id mapping is written from live symbols
The repository MUST contain `docs/v8.2/canonical_id_mapping.md` that records the live id space and no second one. Canonical place id MUST be `places.id`, stored as `TripPlace.place_id`, and copied to GeoJSON point property `place_id`. Stop row id MUST be `TripPlace.id` and GeoJSON point property `trip_place_id`. Day number MUST be `TripPlace.day_number`. Route order MUST be `TripPlace.order_in_day` for routed rows. The document MUST record that narrative prose does not carry place ids, that unknown UUID tokens in that prose are stripped, and that no separate guide-agent UI exists. The document MUST name the sibling frontend change `v83-slice-6-6-trip-map-selection` and the parent vault change `v83-slice-6-canonical-trip-boundary`.

#### Scenario: Mapping doc names the live ids
- **WHEN** a reader opens `docs/v8.2/canonical_id_mapping.md`
- **THEN** it maps `place_id` and `trip_place_id` to the columns and GeoJSON properties above and does not introduce a parallel place id

#### Scenario: Guide prose is recorded as names
- **WHEN** the mapping doc describes the narrative bookend
- **THEN** it states that the bookend is prose, that it must not invent place ids, and that implementation continues to stop status without adding a guide LLM

### Requirement: Canonical trip flag defaults off
`Settings` MUST define `CANONICAL_TRIP_V2_ENABLED` with default false, read only through `get_settings()`. `.env.example` MUST document that name with the default false. While the flag is false, trip JSON and GeoJSON MUST omit `stop_status`, `geometry_provenance`, and `version`, and edit routes MUST ignore `If-Match` and `expected_version`.

#### Scenario: Flag off omits the new keys
- **WHEN** a client fetches a trip or its GeoJSON while `CANONICAL_TRIP_V2_ENABLED` is false
- **THEN** the JSON does not contain `stop_status`, `geometry_provenance`, or `version`

#### Scenario: Flag off ignores a version header
- **WHEN** a client sends `If-Match` on a day edit while the flag is false
- **THEN** the edit is accepted or rejected by today's rules and is not rejected for a version mismatch

### Requirement: Stop status shares the trip place row
`TripPlace` MUST store `stop_status` with exactly the values `confirmed`, `suggested`, `removed`, and `user_added`. Existing rows MUST backfill to `confirmed`. The unique pair `(trip_id, place_id)` MUST stay. Routed statuses MUST be `confirmed` and `user_added` only. `suggested` and `removed` MUST NOT be inputs to the route optimizer, the schedule, or GeoJSON points or lines. `order_in_day` for a non-routed row MUST be 0. Routed `order_in_day` values MUST stay the 1-based route order.

#### Scenario: Suggested row is not a route stop
- **WHEN** a trip has a `suggested` row and a `confirmed` row for different places and the flag is on
- **THEN** GeoJSON points and the day schedule include only the confirmed place

#### Scenario: One row per place
- **WHEN** a place is already `suggested` on a trip and the flag is on
- **THEN** the system does not insert a second `TripPlace` row for that place

### Requirement: Suggestions come from dropped stops and stay off the route
When the flag is on, `save_from_state` MUST, in the same transaction as the routed stops, persist up to `CANONICAL_TRIP_MAX_SUGGESTIONS_PER_DAY` dropped stops per day as `stop_status=suggested` with that day's `day_number` and the dropped stop's canonical `place_id`. The setting MUST default to 3. A dropped id that is already a routed stop on the trip MUST be skipped. A suggestion MUST NOT receive a polyline and MUST NOT change routed `order_in_day`. While the flag is off, save MUST NOT write `suggested` rows. No new HTTP route MAY create a suggestion. No LLM call MAY choose the suggestion list.

#### Scenario: Dropped stop is stored as suggested
- **WHEN** save runs with the flag on and a day schedule lists a dropped stop whose place id is not already routed
- **THEN** that place is stored as `suggested` and is absent from that day's route geometry

#### Scenario: Flag off save writes no suggestions
- **WHEN** save runs with the flag off and the schedule contains dropped stops
- **THEN** the committed trip has no `suggested` row

#### Scenario: Cap drops the rest
- **WHEN** a day has more dropped stops than `CANONICAL_TRIP_MAX_SUGGESTIONS_PER_DAY`
- **THEN** only that many are stored and the route is unchanged

### Requirement: Geometry provenance is osrm, haversine estimate, or none
A persisted routed leg MUST record `geometry_provenance` as `osrm` only when the stored polyline came from a non-fallback road route. It MUST record `haversine_estimate` when the routing backend produced times without a polyline. It MUST record `none` when a road route was attempted and the polyline is missing. A haversine or `none` leg MUST NOT be stored as a synthetic straight polyline. While the flag is off, the column MAY be null and the JSON MUST omit it.

#### Scenario: OSRM polyline is labeled osrm
- **WHEN** a routed stop is saved with a non-null polyline from a non-fallback road route and the flag is on
- **THEN** that stop's provenance is `osrm`

#### Scenario: Haversine day has no line and is not labeled osrm
- **WHEN** the routing backend is haversine and the flag is on
- **THEN** routed stops have null polylines, provenance `haversine_estimate`, and the GeoJSON collection has no LineString

#### Scenario: Failed road route is none
- **WHEN** the routing backend is `osrm` or `hybrid`, the polyline call returns no geometry, and the flag is on
- **THEN** provenance is `none` and no straight LineString is stored

### Requirement: Trip version rejects a stale edit and allows a legacy client
`trips.version` MUST be an integer, not null, default 1. Existing rows MUST backfill to 1. While the flag is on, trip JSON MUST include `version`, and GET and successful edit responses MUST send `ETag` of that integer. An edit that sends `If-Match` or `expected_version` equal to the stored version MUST apply and then increment `version` by 1. An edit that sends a value that does not match MUST return 409 with code `trip_version_conflict` and MUST leave the trip unchanged. If both `If-Match` and `expected_version` are present and differ, the response MUST be 422 and the trip MUST be unchanged. An edit that sends neither MUST still apply and increment `version`. While the flag is off, edits MUST NOT increment `version` and MUST NOT return 409 for a missing or stale version.

#### Scenario: Matching version increments
- **WHEN** the flag is on and the owner reorders with `If-Match` equal to the trip version
- **THEN** the response is 200, the new version is one greater, and the `ETag` matches it

#### Scenario: Mismatch leaves the trip unchanged
- **WHEN** the flag is on and the owner sends a version other than the stored one
- **THEN** the response is 409 `trip_version_conflict` and a following GET shows the previous stops and version

#### Scenario: Legacy edit without a version still works
- **WHEN** the flag is on and the owner calls reoptimize with no `If-Match` and no `expected_version`
- **THEN** the response is 200 and the version has incremented

#### Scenario: Flag off does not bump version
- **WHEN** the flag is off and an edit succeeds
- **THEN** `trips.version` stays at its previous value and the JSON omits `version`
