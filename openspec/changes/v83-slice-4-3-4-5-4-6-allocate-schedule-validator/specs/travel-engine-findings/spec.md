## Purpose

Pure validation findings for the travel engine: a stable code registry, severity, and a deterministic repair hint that does not call tools or I/O.

## ADDED Requirements

### Requirement: Finding model and stable code registry
The project SHALL provide a pure findings module under `src/travel_engine/` with `Severity` (`critical`, `error`, `warning`, `info`) and `ValidationFinding` fields `code`, `severity`, `day`, `stop_ids`, `message`, `repairable`, `suggested_action`, and `blocks_publish`. The code registry MUST contain exactly these codes and MUST NOT drop one: `DUPLICATE_STOP`, `INVALID_COORDINATES`, `MISSING_PLACE_ID`, `OUT_OF_SEARCH_AREA`, `EXCESSIVE_TRAVEL_TIME`, `OVERLOADED_DAY`, `OPENING_HOURS_CONFLICT`, `OPENING_HOURS_UNKNOWN`, `MISSING_ROUTE_GEOMETRY`, `ROUTE_SCHEDULE_MISMATCH`, `NON_CHRONOLOGICAL_SCHEDULE`, `UNREALISTIC_VISIT_SEQUENCE`, `INSUFFICIENT_EVIDENCE`, `MORNING_ONLY_VIOLATION`, `NO_ANCHOR_ATTRACTION`, `GEO_INCOHERENT_DAY`. The module MUST NOT import geo, HTTP, SQLAlchemy, LLM, or `get_settings()`.

#### Scenario: Registry matches the locked set
- **WHEN** the finding code registry is inspected
- **THEN** it contains exactly the sixteen codes above and no other code

#### Scenario: Engine findings module stays pure
- **WHEN** the findings module source is scanned
- **THEN** it does not import geo, HTTP, SQLAlchemy, an LLM client, or `get_settings`

### Requirement: Publish block and repair hint are fixed per code
`blocks_publish` MUST be true only for `DUPLICATE_STOP`, `INVALID_COORDINATES`, `MISSING_PLACE_ID`, `OUT_OF_SEARCH_AREA`, `OPENING_HOURS_CONFLICT`, `MISSING_ROUTE_GEOMETRY`, `ROUTE_SCHEDULE_MISMATCH`, and `NON_CHRONOLOGICAL_SCHEDULE`. Every other code MUST have `blocks_publish` false. `suggested_action` MUST be null or one of `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`. It MUST NOT be `accept_partial` and MUST NOT name a tool outside that set. `repairable` MUST be true only when `suggested_action` is non-null. `OPENING_HOURS_UNKNOWN` and `INSUFFICIENT_EVIDENCE` MUST be severity `info` with null `suggested_action`.

#### Scenario: Critical hours conflict names a route repair
- **WHEN** a finding is built for `OPENING_HOURS_CONFLICT`
- **THEN** `blocks_publish` is true, `repairable` is true, and `suggested_action` is `reoptimize_routes`

#### Scenario: Unknown hours do not demand a repair
- **WHEN** a finding is built for `OPENING_HOURS_UNKNOWN`
- **THEN** severity is `info`, `blocks_publish` is false, `repairable` is false, and `suggested_action` is null

### Requirement: Each code has a valid case and an invalid case
A pure collector MUST emit each registry code on a deliberately invalid fixture and MUST NOT emit that code on a paired valid fixture. Exact repeated place ids MUST emit `DUPLICATE_STOP`. Coordinates outside lat [-90, 90] or lng [-180, 180], or non-finite coordinates, MUST emit `INVALID_COORDINATES`. A stop whose place id is the base sentinel MUST emit `MISSING_PLACE_ID`. `OUT_OF_SEARCH_AREA` MUST be emitted only when a center and radius are supplied and the stop lies outside that radius; when no area is supplied the code MUST NOT be emitted. `MISSING_ROUTE_GEOMETRY` MUST be emitted only when the caller marks geometry as promised and the promised geometry is absent. `OPENING_HOURS_CONFLICT` MUST be emitted only when status is `verified` and the visit interval falls outside the supplied naive window. Status `unknown`, `malformed`, or absent MUST emit `OPENING_HOURS_UNKNOWN` and MUST NOT emit `OPENING_HOURS_CONFLICT`.

#### Scenario: Missing search area is not an out-of-area finding
- **WHEN** findings are collected with no search center and no radius
- **THEN** `OUT_OF_SEARCH_AREA` is absent

#### Scenario: Unknown hours are not a conflict
- **WHEN** a stop has opening status `unknown` and a normal morning start
- **THEN** findings include `OPENING_HOURS_UNKNOWN` and do not include `OPENING_HOURS_CONFLICT`

#### Scenario: Repeated place id is a duplicate
- **WHEN** the same place id appears on two stops
- **THEN** findings include `DUPLICATE_STOP` with `blocks_publish` true
