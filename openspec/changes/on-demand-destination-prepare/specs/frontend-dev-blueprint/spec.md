## ADDED Requirements

### Requirement: FE_guide documents on-demand prepare and guest generate

`docs/FE_guide.md` MUST document `POST /api/v1/destinations/{destination_id}/prepare` (auth None, `ApiResponse` prepare DTO, HTTP 200 `ready` vs 202 `preparing`) in the destinations auth matrix and Live-style endpoint table. The MVP screen flow MUST be: search any place → readiness (may be sparse / `place_count=0`) → **prepare** → poll `GET /destinations/{id}/readiness` until `place_count` meets the planner floor or a client timeout → compose → guest generate. The guide MUST state that generate remains optional auth (no Google login), that 409 `destination_not_ready` means the place floor is unmet (call prepare / wait, do not treat as a stream or login failure), and that guests still open trips via `trip_id` + `wandr_session` (not `GET /trips` list). The guide MUST state that search does not scrape Overpass and that country/region ingest is out of scope. Default JSON client timeout guidance MUST warn that prepare is 202 (do not block 90s on search; poll readiness; do not treat the first sparse poll as failure).

#### Scenario: Frontend author can wire prepare without reading Python

- **WHEN** a frontend developer opens `docs/FE_guide.md` after this change
- **THEN** they find prepare method/path/auth, 200 vs 202, the prepare DTO field names, poll-readiness steps, and 409 vs login guidance in that file

#### Scenario: Guest generate stays no-login in the guide

- **WHEN** the guide describes generate after a newly prepared place
- **THEN** it MUST NOT require Google login or `wandr_token` to search, prepare, generate, or `GET /trips/{id}` for the session that generated the trip

#### Scenario: Empty readiness is not a frontend bug

- **WHEN** search returns a destination with `place_count=0` / score 0
- **THEN** the guide MUST instruct the FE to offer prepare (or equivalent) rather than treating 409 as an auth or SSE client defect
