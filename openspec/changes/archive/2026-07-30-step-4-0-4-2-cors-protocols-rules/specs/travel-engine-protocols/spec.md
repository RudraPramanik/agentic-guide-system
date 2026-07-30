## ADDED Requirements

### Requirement: Routing protocol types are pure and injectable
The project SHALL provide `src/travel_engine/protocols.py` defining:
- `RouteLeg` with `from_place_id`, `to_place_id`, `duration_min`, `distance_km`, `used_fallback`
- `RoutingProvider` Protocol with `async def travel_matrix(waypoints: list[tuple[UUID, float, float]]) -> list[RouteLeg]` returning full directed pairwise legs (`i != j`)
- `legs_to_lookup(legs) -> dict[tuple[UUID, UUID], RouteLeg]`

This module MUST NOT import `src.geo`, `httpx`, SQLAlchemy, litellm, or Qdrant clients. It MUST NOT implement `OsrmRoutingProvider` (deferred to step 4.8).

#### Scenario: RouteLeg indexes via legs_to_lookup
- **WHEN** a `RouteLeg` from A to B is passed to `legs_to_lookup`
- **THEN** lookup[(A, B)].duration_min equals the leg’s duration

#### Scenario: protocols import without geo
- **WHEN** `from src.travel_engine.protocols import RouteLeg, RoutingProvider, legs_to_lookup` is executed
- **THEN** the import succeeds without loading geo gateways
