## Purpose

Locks the shipped HTTP, SSE, and GeoJSON contract in checked-in fixtures so a later slice cannot change paths, envelopes, event names, or geometry shape without a failing test.

## Requirements

### Requirement: Snapshot suite gates the legacy contract
The repository SHALL contain a snapshot suite under `tests/snapshots/` whose expected bodies live under `tests/fixtures/`. `pytest tests/snapshots -v` MUST pass on a clean checkout that has the existing test database and MUST fail when a frozen status, envelope, event name, event order, or GeoJSON geometry type changes.

#### Scenario: Suite command is green
- **WHEN** `pytest tests/snapshots -v` runs against the current checkout with the test database available
- **THEN** every snapshot test passes and none of them open a live geocoder, Overpass, OSRM, LLM, or Qdrant connection

#### Scenario: Contract drift fails the suite
- **WHEN** a frozen response gains or loses an envelope key, renames an SSE event, reorders the frozen event list, or changes a GeoJSON geometry type
- **THEN** `pytest tests/snapshots -v` fails

### Requirement: Volatile fields do not flake
The suite MUST compare normalized bodies. Identifiers, timestamps, and session cookie values MUST be replaced with stable placeholders before comparison. HTTP status, `success`, error `code`, readiness `tier`, SSE event names and order, GeoJSON `type` values, and the set of envelope keys MUST remain exact.

#### Scenario: New identifier still matches
- **WHEN** the same request shape is executed twice and only generated identifiers or timestamps differ
- **THEN** both normalized bodies match the same fixture

#### Scenario: Stable field change fails
- **WHEN** a response changes `success`, an error `code`, a readiness `tier`, an event name, or a geometry `type`
- **THEN** the snapshot comparison fails

### Requirement: Destination search is frozen on a catalog hit
`GET /api/v1/destinations/search` MUST be frozen for a query that matches a destination already in the database. The response MUST be HTTP 200 with `success` true and a `data` array. The suite MUST NOT call the geocoder for that query. `GET /destinations/resolve` and `POST /destinations/{id}/prepare` are outside this suite.

#### Scenario: Seeded search matches the fixture
- **WHEN** a client searches for a name that the test database already contains
- **THEN** the status is 200, the body is an `ApiResponse` whose normalized `data` matches the search fixture, and the geocoder is not called

#### Scenario: Search miss is not a live geocode
- **WHEN** the snapshot suite runs
- **THEN** it does not issue a search whose only result would come from the geocoder

### Requirement: Readiness is frozen without vector search
`GET /api/v1/destinations/{id}/readiness` MUST be frozen for a destination whose counters are seeded in the database while vector search is unavailable. The response MUST be HTTP 200 with `success` true. `tier` MUST be one of `ready`, `limited`, or `sparse`. The suite MUST NOT contact Qdrant.

#### Scenario: Unavailable search matches the fixture
- **WHEN** a client requests readiness for the seeded destination and vector search is unavailable
- **THEN** the status is 200 and the normalized body, including `tier` and `message`, matches the readiness fixture

### Requirement: Planner SSE sequence and the pre-stream floor are frozen
`POST /api/v1/planner/generate` MUST be frozen without running the live planner graph. A scripted progress run MUST yield `text/event-stream` frames whose event names and order match the fixture, and that list MUST end with exactly one terminal event among `itinerary_done`, `error`, and `clarification_needed`. A second terminal emitted by the script MUST NOT appear on the wire. A destination below the planner place-count floor MUST return HTTP 409 with `success` false and `code` `destination_not_ready`, and MUST NOT return SSE frames. The suite MUST NOT require `tool_started` or `validation_done`.

#### Scenario: Scripted progress keeps names and a single terminal
- **WHEN** generate runs for a destination at or above the place-count floor and the planner is stubbed to emit the frozen progress names and then `itinerary_done`
- **THEN** the status is 200, the event names and order match the fixture, and `event: itinerary_done` appears once

#### Scenario: Spurious second terminal is dropped
- **WHEN** the stub emits `itinerary_done` and then another terminal
- **THEN** the response contains exactly one terminal event

#### Scenario: Floor failure is HTTP, not SSE
- **WHEN** generate is called for a destination whose place count is below the planner floor
- **THEN** the status is 409, `code` is `destination_not_ready`, and the body contains no `event:` line

### Requirement: Trip CRUD distinguishes guest and authenticated callers
The suite MUST freeze trip list, get, delete, and claim. `GET /api/v1/trips` without authentication MUST return 401. `GET /api/v1/trips/{id}` with a `wandr_session` cookie equal to the trip session MUST return 200 `ApiResponse`. A mismatched session MUST return 403, not 404. `DELETE /api/v1/trips/{id}` without authentication MUST return 401. `POST /api/v1/trips/{id}/claim` with the matching session and an authenticated owner MUST return 200 `ApiResponse`. List bodies MUST stay a bare paginated object. Get and claim bodies MUST stay `ApiResponse`.

#### Scenario: Anonymous list is rejected
- **WHEN** a client with no credentials calls `GET /api/v1/trips`
- **THEN** the status is 401 and the error envelope matches the frozen unauthorized fixture

#### Scenario: Guest session matches
- **WHEN** a client sends `wandr_session` equal to the trip's session and calls `GET /api/v1/trips/{id}`
- **THEN** the status is 200 and the normalized `ApiResponse` matches the guest-get fixture

#### Scenario: Guest session mismatches
- **WHEN** a client sends a different `wandr_session` and calls `GET /api/v1/trips/{id}`
- **THEN** the status is 403 and the body is not a 404

#### Scenario: Anonymous delete is rejected
- **WHEN** a client with no credentials calls `DELETE /api/v1/trips/{id}`
- **THEN** the status is 401

#### Scenario: Claim with the matching session
- **WHEN** an authenticated client claims an unclaimed trip whose session matches `wandr_session`
- **THEN** the status is 200 and the normalized `ApiResponse` matches the claim fixture

### Requirement: GeoJSON shape is frozen
`GET /api/v1/trips/{id}/geojson` MUST return a raw GeoJSON `FeatureCollection`, not an `ApiResponse`. A trip whose polylines are empty MUST freeze Point features and MUST NOT require a LineString. A trip whose polylines decode MUST freeze at least one LineString. Point properties MUST include `name`, `day`, `order`, `suggested_start_time`, `place_id`, and `trip_place_id`. LineString properties MUST include `day` and `trip_id`. Coordinates MUST be `[lng, lat]`. The read MUST NOT call a routing provider.

#### Scenario: Points only
- **WHEN** geojson is requested for a trip with no decodable polylines
- **THEN** the body is a `FeatureCollection` of Point features, it is not wrapped in `success`/`data`, and it matches the points-only fixture after normalization

#### Scenario: LineString when polylines exist
- **WHEN** geojson is requested for a trip with a decodable polyline
- **THEN** the collection includes a LineString feature and matches the linestring fixture after normalization

### Requirement: Day edits are frozen without a routing provider
The four day-edit routes MUST be frozen for an authenticated owner, using injected routing times rather than a live routing service. Each success response MUST be HTTP 200 `ApiResponse`. Each route without authentication MUST return 401. The routes are `PATCH /api/v1/trips/{id}/days/{day}/stops/reorder`, `DELETE /api/v1/trips/{id}/days/{day}/stops/{place_id}`, `POST /api/v1/trips/{id}/days/{day}/stops`, and `POST /api/v1/trips/{id}/days/{day}/reoptimize`.

#### Scenario: Owner reorder matches the fixture
- **WHEN** the trip owner reorders stops on a day
- **THEN** the status is 200 and the normalized trip body matches the reorder fixture

#### Scenario: Owner remove, add, and reoptimize match their fixtures
- **WHEN** the trip owner removes a stop, adds a stop, and reoptimizes a day, each as its own request
- **THEN** each status is 200 and each normalized body matches its fixture

#### Scenario: Anonymous edit is rejected
- **WHEN** a client with no credentials calls any of the four day-edit routes
- **THEN** the status is 401 and no routing provider is contacted
