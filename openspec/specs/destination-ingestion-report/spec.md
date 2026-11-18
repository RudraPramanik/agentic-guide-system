## Purpose

Reports ingestion quality for a destination from checked-in fixtures, without an HTTP endpoint or a live provider call.

## Requirements

### Requirement: The ingestion report is a script over three fixtures

The system SHALL provide a script that reads checked-in fixtures for Darjeeling, Manali, and Goa and writes one JSON document to stdout. The script MUST NOT register an HTTP route, MUST NOT open a database, and MUST NOT call Overpass, Qdrant, or any other network. Each fixture MUST supply its own `as_of` date. Freshness MUST be computed against that date, not the wall clock.

For each destination the document MUST include the place count, a category-to-count map, the duplicate rate, the failure count, the failure reasons, and the freshness share. Duplicate rate MUST be `(input count - usable count) / input count`, using the same id and same-name-within-150-meters collapse as Readiness V2. An empty place list MUST report count 0 and duplicate rate 0. Freshness share MUST be the fraction of places whose retrieval timestamp is within 30 days before `as_of`, inclusive of day 30. A place with no timestamp MUST count as not fresh.

A missing fixture, a fixture that is not an object, or a destination entry missing any of those output fields MUST make the script exit non-zero and MUST name the destination. Three well-formed fixtures MUST make the script exit 0.

#### Scenario: Three fixtures print three destinations

- **WHEN** the script runs against the Darjeeling, Manali, and Goa fixtures
- **THEN** stdout is one JSON document containing those three destination names, and the process exits 0

#### Scenario: Duplicate rate matches a known pair

- **WHEN** a fixture has two same-name places 100 meters apart and no other places
- **THEN** that destination's place count contribution to the duplicate rate uses an input count of 2 and a usable count of 1, so the rate is 0.5

#### Scenario: Stale and missing timestamps are not fresh

- **WHEN** `as_of` is 2026-01-31, one place was retrieved on 2025-12-01, and another place has no timestamp
- **THEN** the freshness share counts neither place as fresh

#### Scenario: A missing fixture fails the script

- **WHEN** the Goa fixture path is absent
- **THEN** the process exits non-zero and the output names Goa

### Requirement: The report does not invent failures

Failure rows MUST be echoed from the fixture. The script MUST NOT classify a live provider error, because it MUST NOT call a provider. An empty failure list MUST report failure count 0.

#### Scenario: Fixture failures are copied

- **WHEN** the Darjeeling fixture lists one failure reason `overpass_timeout`
- **THEN** the Darjeeling section of the report has failure count 1 and that reason
