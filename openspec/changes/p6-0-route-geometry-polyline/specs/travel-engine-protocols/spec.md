## ADDED Requirements

### Requirement: RoutingProvider declares route_polyline
`RoutingProvider` in `src/travel_engine/protocols.py` MUST declare:

```
async def route_polyline(self, waypoints: list[tuple[float, float]]) -> str | None
```

for an ordered waypoint list. Semantics: return encoded polyline geometry for the path through the waypoints in order when available; return `None` when unavailable; MUST NOT raise for missing geometry. This is a Protocol surface only — no I/O in `travel_engine`. Geometry is requested **after** route order is chosen, not as a substitute for `travel_matrix`.

#### Scenario: Protocol includes route_polyline
- **WHEN** `RoutingProvider` is inspected
- **THEN** it declares `route_polyline` alongside `travel_matrix`

#### Scenario: travel_engine still has no geo imports
- **WHEN** modules under `src/travel_engine/` are scanned for geo/httpx imports
- **THEN** there are zero matches
