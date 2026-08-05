## ADDED Requirements

### Requirement: OptimizeResult includes post-order polylines
`OptimizeResult` MUST include:

- `leg_polylines: list[str | None]` — length equals `len(ordered)`; index `i` is the polyline into `ordered[i]` from the previous waypoint (base for `i=0`)
- `day_polyline: str | None` — aggregate polyline for base + all ordered stops in order

After the final winning ordered list is selected (after drop-retry settles), `optimize_route` MUST call `routing.route_polyline` for each consecutive pair in `[(base_lat, base_lng)] + stop coords`, then once for the full waypoint list. It MUST NOT call `route_polyline` inside the permutation scoring loop or for discarded drop-retry candidates. Empty `ordered` MUST leave both fields empty/None with no geometry calls. All-None polylines MUST NOT abort optimization.

#### Scenario: Three stops yield three leg polylines plus day
- **WHEN** optimize returns three ordered stops and `route_polyline` returns deterministic non-None strings
- **THEN** `len(leg_polylines) == 3` and `day_polyline` is not None

#### Scenario: Geometry failure is soft
- **WHEN** `route_polyline` returns `None` for all calls
- **THEN** optimize still returns ordered stops / legs / travel totals with all-None polyline fields and does not raise

#### Scenario: No geometry during permutation search
- **WHEN** a Fake provider counts `route_polyline` calls during an optimize with multiple permutations
- **THEN** call count is ≤ `len(ordered) + 1` for the returned result (not proportional to permutation count)
