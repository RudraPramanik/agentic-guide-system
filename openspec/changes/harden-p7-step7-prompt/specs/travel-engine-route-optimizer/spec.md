## ADDED Requirements

### Requirement: Shared polyline population for fixed-order and optimize callers

The project SHALL expose a reusable async helper in `src/travel_engine/route_optimizer.py` (promoted from `_populate_polylines` or equivalent public name) that, given an already-decided `ordered` list, `base_lat`/`base_lng`, and `RoutingProvider`, returns `leg_polylines` and `day_polyline` using the same N+1 `route_polyline` pattern as today. `optimize_route` MUST call this helper for the winning order and MUST continue to set `OptimizeResult.legs` to the **full pairwise** matrix from `travel_matrix` (MUST NOT replace legs with consecutive-only). Fixed-order P7 reorder MUST reuse the same polyline helper after computing consecutive legs for the user order — MUST NOT duplicate independent polyline loops. Pure travel_engine constraints unchanged (RoutingProvider only; no geo/httpx/DB).

#### Scenario: optimize_route still returns full pairwise legs

- **WHEN** `optimize_route` runs for three stops with a Fake full matrix
- **THEN** `len(result.legs)` equals the full directed pairwise matrix size among BASE + stops (12 for 3 stops), not merely 3 consecutive hops

#### Scenario: Fixed-order path reuses polyline helper

- **WHEN** a fixed-order geometry path is invoked for two stops
- **THEN** `leg_polylines` length is 2 and polyline calls use the shared helper (not a separate copy of the loop)

#### Scenario: Existing polyline soft-fail behavior preserved

- **WHEN** `route_polyline` returns None for all calls after the shared-helper refactor
- **THEN** optimize still returns ordered stops with all-None polyline fields and does not raise
