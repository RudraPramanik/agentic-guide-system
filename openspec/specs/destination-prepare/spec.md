## Purpose

Public, unauthenticated prepare/seed for a geocoded destination: scrape places in a radius around the stored point so `place_count` can meet the planner floor, without country ingest or login.

## Requirements

### Requirement: Public prepare seeds places for an existing destination

The system SHALL provide a public (no auth) prepare operation for an existing destination that fetches Overpass POIs around that destination’s stored `lat`/`lng` within a radius (default 30 km, maximum 50 km) and upserts places, then updates `place_count` to the success count. Prepare MUST NOT call Nominatim/Overpass/httpx except through `src/geo/`. Prepare MUST NOT run LLM enrich or Qdrant index. Prepare MUST NOT scrape a country or region polygon. Unknown destination ids MUST surface as 404 `not_found`.

#### Scenario: Empty shell becomes plannable after prepare

- **WHEN** a destination exists with `place_count` below `PLANNER_ABSOLUTE_MIN_PLACES` and Overpass returns enough POIs
- **THEN** after prepare completes, `place_count` is at least `PLANNER_ABSOLUTE_MIN_PLACES` and `POST /planner/generate` for that id is no longer refused solely for the place-count floor

#### Scenario: Unknown destination is 404

- **WHEN** prepare is requested for a UUID that does not exist
- **THEN** the response is 404 with code `not_found` and no Overpass call is required

#### Scenario: Country polygon is out of scope

- **WHEN** prepare runs for a geocoded place
- **THEN** POIs are fetched only within the requested radius of the stored point (not a country/region boundary)

### Requirement: Prepare is kickoff-then-poll, not a blocked search

The system SHALL start Overpass seeding without requiring the client to hold the search HTTP connection. If `place_count` is already at or above `PLANNER_ABSOLUTE_MIN_PLACES`, prepare MUST return HTTP 200 with status `ready` and MUST NOT start another scrape. Otherwise prepare MUST return HTTP 202 with status `preparing` and run the scrape asynchronously. A concurrent prepare for the same destination while one is in flight MUST also return 202 `preparing` and MUST NOT start a second scrape. Clients MUST observe progress via existing `GET /destinations/{id}/readiness` (`place_count` / `tier`). Empty Overpass results MUST leave the destination persisted with `place_count` unchanged or zero as the seed pipeline already does (destination row remains; generate still 409 until the floor is met).

#### Scenario: Already seeded destination is a no-op

- **WHEN** prepare is called for a destination whose `place_count` is already at or above `PLANNER_ABSOLUTE_MIN_PLACES`
- **THEN** the response is 200 with status `ready` and Overpass is not invoked

#### Scenario: Unseeded destination returns 202

- **WHEN** prepare is called for an existing destination below the planner place floor and no scrape is in flight
- **THEN** the response is 202 with status `preparing` and a scrape starts

#### Scenario: Concurrent prepare does not double-scrape

- **WHEN** a second prepare arrives for the same destination while a scrape is in flight
- **THEN** the second response is 202 with status `preparing` and a second Overpass fetch is not started

#### Scenario: Client learns completion from readiness

- **WHEN** a client has received 202 and later `GET /destinations/{id}/readiness` shows `place_count` at or above `PLANNER_ABSOLUTE_MIN_PLACES`
- **THEN** the client MAY call `POST /planner/generate` without treating the earlier sparse readiness snapshot as a permanent failure

### Requirement: Prepare does not require login

Prepare MUST be callable without `wandr_token` / Google login (auth None). Guest session cookies MUST NOT be required to start prepare. Guest generate and `GET /trips/{id}` session ownership MUST remain unchanged (optional auth + `wandr_session` match).

#### Scenario: Anonymous client can prepare

- **WHEN** a client with no `wandr_token` posts prepare for a known destination
- **THEN** the call is not rejected with 401 `unauthorized`
