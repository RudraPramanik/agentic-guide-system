## Purpose

Selects a RoutingProvider that keeps generate/edit travel times in-process while fetching fail-soft OSRM road geometries for itinerary polylines after stop order is fixed.

## ADDED Requirements

### Requirement: Hybrid provider uses haversine matrix and OSRM polylines
The system SHALL provide a hybrid `RoutingProvider` adapter (name may be `HybridRoutingProvider` or equivalent) whose `travel_matrix` builds the full directed i≠j `RouteLeg` set using the public in-process estimate helper (haversine × 1.4, 30 km/h) with `used_fallback=True` on every leg and MUST NOT call `get_route` or any OSRM HTTP URL for the matrix. Its `route_polyline` MUST delegate to the same fail-soft OSRM geometry rules as `OsrmRoutingProvider.route_polyline` (encoded string when live geometry succeeds; `None` on fallback, missing geometry, or errors — never raise to callers). Geo I/O MUST remain in `src/geo/` only; `travel_engine` MUST keep zero geo imports.

#### Scenario: Matrix never hits OSRM HTTP
- **WHEN** hybrid `travel_matrix` is called with three waypoints
- **THEN** the result contains exactly six directed legs each with `used_fallback=True` and no OSRM HTTP client is used for those legs

#### Scenario: Polyline uses live geometry when available
- **WHEN** hybrid `route_polyline` is called with ≥2 waypoints and the underlying route result is non-fallback with a non-empty encoded polyline
- **THEN** the returned value is that encoded polyline string

#### Scenario: Polyline soft-fails like OSRM adapter
- **WHEN** hybrid `route_polyline` encounters fallback, missing geometry, or an error from the geo route helper
- **THEN** the return value is `None` and no exception propagates to the caller

### Requirement: Settings select hybrid as a routing backend
The system SHALL accept `ROUTING_BACKEND` value `hybrid` (in addition to existing `haversine` and `osrm`) via `get_settings()` only. Unknown values MUST continue to fail-soft to `haversine`. The default MAY remain `haversine` or become `hybrid` only if documented in `docs/context.md` and `.env.example` without forcing full-matrix OSRM.

#### Scenario: hybrid backend is selectable
- **WHEN** `ROUTING_BACKEND` is `hybrid`
- **THEN** `get_settings().ROUTING_BACKEND` is `hybrid` and `get_routing_provider()` returns the hybrid adapter

#### Scenario: Unknown backend still haversine
- **WHEN** `ROUTING_BACKEND` is an unrecognized value
- **THEN** `get_routing_provider()` returns the haversine-only adapter
