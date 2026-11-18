## MODIFIED Requirements

### Requirement: Per-op day surgery semantics

The system SHALL apply these semantics:

- **reorder:** `place_ids` MUST satisfy `len(place_ids) == len(current)` AND `set(place_ids) == set(current)`; preserve client order through a **preserve-order** schedule path (MUST NOT run morning-extract reorder); recompute times + polylines via fixed-order matrix/geometry; MUST NOT call `optimize_route`.
- **remove:** if stop not on that day → 404 `stop_not_found_on_day`; if day would have zero stops → 422 `day_would_be_empty`; else `optimize_route` + schedule + polylines for remaining.
- **add:** insert at end then `optimize_route` + schedule + polylines; wrong destination → 422; duplicate on trip → 409 `stop_already_on_trip`; non-empty `dropped_stops` → 422 `edit_would_drop_other_stops` + rollback (no silent drop).
- **reoptimize:** `optimize_route` + schedule + polylines; same non-empty `dropped_stops` → 422 rule as add.

Hydration to `ScoredPlace` MUST use Place coords/category/tags via `to_shape` and **score=1.0**. Polylines MUST be written to `TripPlace.polyline` from parallel `leg_polylines` at persist — MUST NOT invent `ScheduledStop.leg_polyline` / `DayPlan.day_polyline` fields.

While `CANONICAL_TRIP_V2_ENABLED` is false, `current` for reorder and the day membership for remove MUST be every `TripPlace` on that day, remove MUST hard-delete the row, and add of a place that already has any row on the trip MUST be 409 `stop_already_on_trip`.

While the flag is true, `current` and day membership MUST be routed rows only (`confirmed` and `user_added`). `suggested` and `removed` rows MUST NOT count toward `day_would_be_empty` and MUST NOT be part of a reorder permutation. Remove of a routed stop MUST set that row to `removed`, clear its polyline, set `order_in_day` to 0, and recompute the remaining routed stops. It MUST NOT hard-delete the row. Add of a `suggested` or `removed` row for that place MUST reuse the row, set `stop_status` to `user_added`, and optimize it onto the route. Add of a place that is already `confirmed` or `user_added` anywhere on the trip MUST still be 409 `stop_already_on_trip`. A successful add MUST NOT leave the new stop as `suggested`.

#### Scenario: Reorder preserves user order

- **WHEN** owner reorders day stops to a specific permutation
- **THEN** persisted `order_in_day` matches that permutation exactly (no TSP and no morning-extract reordering)

#### Scenario: Remove last stop rejected

- **WHEN** owner deletes the only remaining stop on a day
- **THEN** response is 422 `day_would_be_empty` and the stop remains

#### Scenario: Add that would drop another stop is rejected

- **WHEN** adding a stop causes `optimize_route` to return non-empty `dropped_stops`
- **THEN** response is 422 `edit_would_drop_other_stops` with details naming would-drop places, and zero TripPlace rows change

#### Scenario: Stop not on day is 404

- **WHEN** owner DELETEs a `place_id` that is not on that day
- **THEN** response is 404 `stop_not_found_on_day`

#### Scenario: Duplicate reorder ids rejected

- **WHEN** owner submits a reorder list with duplicate ids (same length trick fails set equality)
- **THEN** response is 422 and the trip is unchanged

#### Scenario: Flag on add promotes a suggestion
- **WHEN** the flag is true and the owner POSTs add for a place that is `suggested` on that trip
- **THEN** the response is 200, that row's `stop_status` is `user_added`, and the place is in the day's routed order

#### Scenario: Flag on remove keeps the row
- **WHEN** the flag is true and the owner removes a routed stop that is not the day's last routed stop
- **THEN** the row remains with `stop_status=removed` and it is absent from GeoJSON

#### Scenario: Flag off remove still hard-deletes
- **WHEN** the flag is false and the owner removes a stop
- **THEN** that `TripPlace` row is gone and the remaining stops are reordered

### Requirement: TripEditEvent on every successful edit

Each successful P7 edit MUST insert **exactly one** `TripEditEvent` created by `TripService`/`TripRepository` (not by EvaluationService), with correct `EditType`, `day_number`, optional `place_id`, and before/after payload, in the same transaction as TripPlace mutations. While `CANONICAL_TRIP_V2_ENABLED` is false, concurrent edits to the same trip remain last-write-wins with no row locking. While the flag is true, a second edit whose `If-Match` or `expected_version` does not match the version stored after the first commit MUST be 409 `trip_version_conflict` and MUST NOT write a `TripEditEvent`.

#### Scenario: Successful reorder writes one audit row

- **WHEN** reorder succeeds
- **THEN** exactly one new `TripEditEvent` with `edit_type=reorder` exists for that trip_id for the attempt

#### Scenario: Stale second edit writes no audit row
- **WHEN** the flag is true and a second edit sends the version from before the first edit committed
- **THEN** the response is 409 and the `TripEditEvent` count increased only for the first edit

## ADDED Requirements

### Requirement: Flag-on edits roll back on a blocking validator V2 finding
When `CANONICAL_TRIP_V2_ENABLED` is true, a day edit MUST run `collect_findings` on the rebuilt itinerary of routed stops after the existing `validate_trip` check. A finding with `blocks_publish` true MUST roll the transaction back and return 422, and MUST NOT write a `TripEditEvent`, except `MISSING_ROUTE_GEOMETRY`. The edit path MUST pass geometry as not promised for every current routing backend (`haversine`, `hybrid`, and `osrm`), because those backends are fail-soft and do not promise a road line. A null polyline MUST NOT by itself fail the edit. `VALIDATOR_V2_ENFORCE` MUST stay false and MUST NOT be what gates this edit check. When the flag is false, the edit path MUST NOT reject a trip for a V2 finding.

#### Scenario: Blocking finding leaves the trip unchanged
- **WHEN** the flag is true and the rebuilt day produces a finding with `blocks_publish` true
- **THEN** the response is 422 and a following GET matches the pre-edit trip

#### Scenario: Haversine edit is not blocked for a missing line
- **WHEN** the flag is true, the routing backend is haversine, and the only missing geometry is a null polyline
- **THEN** the edit is not rejected with `MISSING_ROUTE_GEOMETRY`

#### Scenario: Road-router outage still commits the edit
- **WHEN** the flag is true, the routing backend is `hybrid` or `osrm`, and `route_polyline` returns no geometry
- **THEN** the response is 200, provenance on the rewritten routed legs is `none`, and the edit is not rejected with `MISSING_ROUTE_GEOMETRY`

#### Scenario: Flag off edit ignores V2 findings
- **WHEN** the flag is false and a V2 finding would have `blocks_publish` true
- **THEN** the edit result matches today's `validate_trip` rules and is not failed for that finding
