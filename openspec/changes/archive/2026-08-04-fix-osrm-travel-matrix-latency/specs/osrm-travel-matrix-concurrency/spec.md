## ADDED Requirements

### Requirement: Travel matrix uses bounded concurrency
The system SHALL complete `OsrmRoutingProvider.travel_matrix` by issuing pairwise `get_route` calls with bounded concurrency controlled by `get_settings().OSRM_MATRIX_MAX_CONCURRENCY` (positive integer; default 8). The provider MUST NOT await every pair strictly in serial nested-loop order when more than one pair is pending. Peak in-flight `get_route` calls for a single `travel_matrix` invocation MUST NOT exceed the configured concurrency. Leg semantics (all directed i≠j pairs, duration/distance/fallback mapping) MUST remain unchanged. Modules under `src/travel_engine/` MUST continue to have zero geo imports.

#### Scenario: Concurrent matrix respects semaphore
- **WHEN** `travel_matrix` is invoked with four or more waypoints and `get_route` is instrumented with artificial latency
- **THEN** the matrix returns the full set of directed legs and the observed peak concurrent `get_route` calls is ≤ `OSRM_MATRIX_MAX_CONCURRENCY`

#### Scenario: Wall time improves vs serial for multi-waypoint matrix
- **WHEN** `get_route` is mocked to sleep a fixed delay D per call and waypoints ≥ 4
- **THEN** `travel_matrix` wall time is substantially less than `(n*(n-1))*D` serial cost (allowing for semaphore batching)

### Requirement: Matrix concurrency is settings-driven
The project SHALL expose `OSRM_MATRIX_MAX_CONCURRENCY` on Settings (loaded only via `get_settings()`), document it in `.env.example` with a safe default for public OSRM, and MUST NOT read this value through raw `os.environ` in planner or geo modules.

#### Scenario: Settings expose concurrency knob
- **WHEN** an operator sets `OSRM_MATRIX_MAX_CONCURRENCY` in env
- **THEN** `get_settings().OSRM_MATRIX_MAX_CONCURRENCY` reflects that value and `travel_matrix` uses it for the semaphore limit
