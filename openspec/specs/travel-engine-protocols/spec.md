## Purpose

Pure routing injection types for `travel_engine` — `RouteLeg`, `RoutingProvider`, and lookup helpers with no geo/network/DB I/O.

## Requirements

### Requirement: Routing protocol types are pure and injectable
The project SHALL provide `src/travel_engine/protocols.py` defining:
- `RouteLeg` with `from_place_id`, `to_place_id`, `duration_min`, `distance_km`, `used_fallback`
- `RoutingProvider` Protocol with `async def travel_matrix(waypoints: list[tuple[UUID, float, float]]) -> list[RouteLeg]` returning full directed pairwise legs (`i != j`)
- `RoutingProvider.route_polyline(waypoints: list[tuple[float, float]]) -> str | None` — encoded geometry after order is chosen; `None` when unavailable; MUST NOT raise for missing geometry (Protocol surface only; no I/O in `travel_engine`)
- `legs_to_lookup(legs) -> dict[tuple[UUID, UUID], RouteLeg]`

This module MUST NOT import `src.geo`, `httpx`, SQLAlchemy, litellm, or Qdrant clients. It MUST NOT implement `OsrmRoutingProvider` (deferred to step 4.8; adapter lives under `src/planner/`).

#### Scenario: RouteLeg indexes via legs_to_lookup
- **WHEN** a `RouteLeg` from A to B is passed to `legs_to_lookup`
- **THEN** lookup[(A, B)].duration_min equals the leg’s duration

#### Scenario: protocols import without geo
- **WHEN** `from src.travel_engine.protocols import RouteLeg, RoutingProvider, legs_to_lookup` is executed
- **THEN** the import succeeds without loading geo gateways

#### Scenario: Protocol includes route_polyline
- **WHEN** `RoutingProvider` is inspected
- **THEN** it declares `route_polyline` alongside `travel_matrix`

#### Scenario: travel_engine still has no geo imports
- **WHEN** modules under `src/travel_engine/` are scanned for geo/httpx imports
- **THEN** there are zero matches
