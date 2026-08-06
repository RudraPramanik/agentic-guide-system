## MODIFIED Requirements

### Requirement: Shared polyline population for fixed-order and optimize callers

The project SHALL expose a reusable public async helper `populate_leg_polylines` in `src/travel_engine/route_optimizer.py` (promoted from `_populate_polylines`) that, given an already-decided `ordered: list[ScoredPlace]`, `base_lat`, `base_lng`, and `RoutingProvider`, returns `(leg_polylines, day_polyline)` using the same N+1 `route_polyline` pattern: one call per consecutive pair in `[(base_lat, base_lng)] + stop coords`, then one call for the full waypoint list. Empty `ordered` MUST return `([], None)` with no geometry calls. Soft-fail `None` polylines MUST NOT raise.

`optimize_route` MUST call `populate_leg_polylines` for the winning order after drop-retry settles and MUST continue to set `OptimizeResult.legs` to the **full pairwise** matrix from `travel_matrix` (MUST NOT replace legs with consecutive-only). The helper MUST NOT perform permutation search or drop-retry. Fixed-order P7 reorder (step 7.2) MUST reuse this helper after computing consecutive legs for the user order — MUST NOT duplicate an independent polyline loop. Pure travel_engine constraints unchanged (RoutingProvider only; no geo/httpx/DB).

An optional consecutive-legs helper (e.g. matrix-once for `[BASE + ordered]`) MAY exist in the same module for 7.2, but MUST NOT be wired as a drop-in replacement for `OptimizeResult.legs`.

#### Scenario: optimize_route still returns full pairwise legs

- **WHEN** `optimize_route` runs for three stops with a Fake full matrix
- **THEN** `len(result.legs)` equals the full directed pairwise matrix size among BASE + stops (12 for 3 stops), not merely 3 consecutive hops, and `len(result.leg_polylines) == 3`

#### Scenario: Public helper callable for fixed order

- **WHEN** `populate_leg_polylines` is invoked directly for two already-ordered stops with a Fake provider
- **THEN** `leg_polylines` length is 2 and `route_polyline` call count is ≤ 3 (two legs + day)

#### Scenario: Existing polyline soft-fail behavior preserved

- **WHEN** `route_polyline` returns None for all calls after the shared-helper refactor
- **THEN** optimize still returns ordered stops with all-None polyline fields and does not raise

#### Scenario: No geometry during permutation search

- **WHEN** a Fake provider counts `route_polyline` calls during an optimize with multiple permutations
- **THEN** call count is ≤ `len(ordered) + 1` for the returned result (not proportional to permutation count)
