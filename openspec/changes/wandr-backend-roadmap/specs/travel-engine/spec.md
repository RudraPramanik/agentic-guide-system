## ADDED Requirements

### Requirement: Pure Python travel intelligence

The `travel_engine/` package SHALL contain no LLM calls, network I/O, or database access. Routing times MUST be injected via `RoutingProvider` protocol.

#### Scenario: Import without geo dependency

- **WHEN** `travel_engine` modules are imported
- **THEN** no import from `src/geo/` occurs

### Requirement: Place selection

The system SHALL rank and filter candidate POIs in `place_selector.py` using category weights, exclusion rules, and conflict pairs.

#### Scenario: Photography preference boosts viewpoints

- **WHEN** 36 candidates are selected with photography interest
- **THEN** photography-tagged places score higher than unrelated categories

### Requirement: Day allocation

The system SHALL split selected places into day buckets capped at `MAX_PLACES_PER_DAY` with geographic pre-clustering.

#### Scenario: Three-day allocation

- **WHEN** 18 places are allocated across 3 days
- **THEN** each day has ≤6 places and visit time fits 8-hour budget

### Requirement: Route optimization

The system SHALL order stops per day via `route_optimizer.py` calling injected `RoutingProvider`, dropping weakest stops if travel exceeds daily cap (max 3 retries).

#### Scenario: Fake routing provider unit test

- **WHEN** unit tests use `FakeRoutingProvider`
- **THEN** route optimization completes without network

### Requirement: Schedule builder

The system SHALL assign `suggested_start_time` and `visit_duration_min` in `schedule_builder.py` with morning-only and lunch break rules.

#### Scenario: Morning viewpoint in slot 1 or 2

- **WHEN** a day includes a morning-only viewpoint category
- **THEN** that stop appears in order ≤2 with start time ≤ 10:30

### Requirement: Trip validator

The system SHALL validate itineraries in `trip_validator.py` returning `ValidationResult` with errors and warnings.

#### Scenario: Valid itinerary passes

- **WHEN** a well-formed itinerary is validated
- **THEN** `passed=True` and `errors=[]`

### Requirement: OSRM routing provider adapter

The system SHALL provide `OsrmRoutingProvider` in `src/planner/routing_provider.py` implementing `RoutingProvider` by wrapping `geo/osrm.py`.

#### Scenario: Fallback flag on haversine

- **WHEN** OSRM fails and haversine fallback is used
- **THEN** `used_osrm_fallback` signal is set on planner state
