## ADDED Requirements

### Requirement: OsrmRoutingProvider implements RoutingProvider

The system MUST provide `OsrmRoutingProvider` in `src/planner/routing_provider.py` that implements `travel_engine.protocols.RoutingProvider` by calling `src.geo.osrm` (never importing OSRM HTTP details into travel_engine). When the geo layer uses haversine fallback, legs MUST set `used_fallback=True` so callers can set planner state flags later.

#### Scenario: Fallback flag on legs
- **WHEN** the underlying OSRM path falls back to haversine × 1.4
- **THEN** returned `RouteLeg` objects MUST have `used_fallback=True`

#### Scenario: travel_engine stays geo-free
- **WHEN** `src/travel_engine` modules are inspected for imports
- **THEN** they MUST NOT import `src.geo` or `src.planner.routing_provider`

### Requirement: ToolResult execute_tool skeleton

The system MUST provide a minimal `execute_tool(name, input, ctx) -> ToolResult` skeleton and `ToolResult` envelope that logs and never raises uncaught exceptions to callers. Full tool registry and phase gating MAY remain stubbed until P5, but the envelope shape MUST be usable by unit tests.

#### Scenario: Unknown tool returns failed result
- **WHEN** `execute_tool` is called with a name not in the stub registry
- **THEN** it MUST return `ToolResult(ok=False)` (or equivalent) and MUST NOT raise

#### Scenario: Stub does not call travel_engine side effects by default
- **WHEN** only the P4 stub is present
- **THEN** registered tool bodies MAY be no-ops or placeholders, with real tool logic deferred to P5
