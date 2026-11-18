## Purpose

P7 day-scoped trip edit HTTP API and TripService day surgery (v2.1 locks from `docs/steps/step7.md`). Implementation lands in steps 7.1–7.4; this spec is the behavior contract.

## Requirements

### Requirement: Day-scoped edit HTTP API

The system SHALL expose these authenticated endpoints under `/api/v1/trips` via `src/trips/router.py` (registered on the FastAPI app; visible in OpenAPI):

| Method | Path | Body |
|--------|------|------|
| PATCH | `/{id}/days/{day}/stops/reorder` | `{ "place_ids": [uuid, ...] }` (`ReorderStopsIn`) |
| DELETE | `/{id}/days/{day}/stops/{place_id}` | — |
| POST | `/{id}/days/{day}/stops` | `{ "place_id": uuid }` (`AddStopIn`) |
| POST | `/{id}/days/{day}/reoptimize` | — |

Each successful response MUST be `ApiResponse[TripOut]`. All four MUST use `require_auth` (via `rate_limit_trip_edit` or equivalent chain) and ownership (`trip.user_id == caller`); guests MUST NOT edit via session alone (claim first). Ownership miss → 403; missing/soft-deleted trip → 404. Edit routes MUST apply a user-keyed rate-limit dependency (`rate_limit_trip_edit`) in addition to any global middleware default; exceeded limit → 429. Paths MUST NOT be added as broken exact-match UUID entries in `_route_limit_table`. Router MUST call `TripService` only (no repository/DB, no `travel_engine`, no planner/LLM imports). Domain errors MUST surface through the global `WandrError` handler (422/409/404/403 as raised by the service).

#### Scenario: OpenAPI lists four edit routes

- **WHEN** the FastAPI OpenAPI schema is inspected after step 7.3
- **THEN** it includes the four paths above under the trips tag

#### Scenario: Owner reorder returns TripOut

- **WHEN** the authenticated owner PATCHes reorder with a valid permutation of day stops
- **THEN** the response is 200 `ApiResponse[TripOut]` and stop `order_in_day`, times, and polylines reflect the requested order

#### Scenario: Guest cannot edit

- **WHEN** an unauthenticated or guest-only caller invokes any P7 edit endpoint
- **THEN** the response is 401 (or auth challenge) and the trip is unchanged

#### Scenario: Non-owner is forbidden

- **WHEN** an authenticated user who does not own the trip calls a P7 edit endpoint
- **THEN** the response is 403 and the trip is unchanged

#### Scenario: Edit rate limit exceeded

- **WHEN** the same authenticated user exceeds `RATE_LIMIT_TRIP_EDIT_REQUESTS` within the window
- **THEN** the response is 429 and the trip is unchanged

#### Scenario: Validation failure leaves trip unchanged

- **WHEN** an authenticated owner POSTs add that would drop other stops (or otherwise fails service validation)
- **THEN** the response is 422 and a subsequent GET matches the pre-edit trip

### Requirement: Edit path uses travel_engine not planner agent

`TripService` edit operations MUST call pure `travel_engine` functions and an injected `RoutingProvider`. They MUST NOT call `PlannerService`, `execute_tool`, LangGraph, or planner tool implementation modules. No LLM calls on the edit path.

#### Scenario: Service has no PlannerService dependency

- **WHEN** `TripService` edit methods are inspected / imported
- **THEN** they do not import or invoke `PlannerService` or `execute_tool`

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

### Requirement: Validation failure rolls back with reorder morning exception

After an edit attempt, the system MUST run `validate_trip` on a rebuilt itinerary. Unchanged days MUST be reconstructed from stored `TripPlace` fields only (zero additional RoutingProvider calls). If validation `errors` remain non-empty after any reorder-specific downgrade, the transaction MUST roll back and HTTP MUST be 422 with validation details. For **reorder only**, errors that are morning-slot violations MUST be downgraded to warnings and commit MAY proceed. Other edit types MUST keep morning-slot errors as hard failures. OSRM fallback MUST NOT produce HTTP 500.

#### Scenario: Validation errors roll back

- **WHEN** `validate_trip` returns non-morning errors (or any errors on non-reorder edits)
- **THEN** response is 422, trip unchanged, and no new `TripEditEvent` is committed

#### Scenario: Reorder morning-slot-only still commits

- **WHEN** reorder validation would only fail morning-slot rules
- **THEN** response is 200, warnings present, and the user’s order is persisted

#### Scenario: Unchanged days skip routing

- **WHEN** a multi-day trip is edited on day 1 only
- **THEN** RoutingProvider calls reflect only the mutated day’s matrix/polyline work

#### Scenario: OSRM fail during reoptimize

- **WHEN** OSRM is unavailable during reoptimize and the provider falls back
- **THEN** the response is 200 (not 500) and day times are updated (polylines may be null)

### Requirement: TripEditEvent on every successful edit

Each successful P7 edit MUST insert **exactly one** `TripEditEvent` created by `TripService`/`TripRepository` (not by EvaluationService), with correct `EditType`, `day_number`, optional `place_id`, and before/after payload, in the same transaction as TripPlace mutations. While `CANONICAL_TRIP_V2_ENABLED` is false, concurrent edits to the same trip remain last-write-wins with no row locking. While the flag is true, a second edit whose `If-Match` or `expected_version` does not match the version stored after the first commit MUST be 409 `trip_version_conflict` and MUST NOT write a `TripEditEvent`.

#### Scenario: Successful reorder writes one audit row

- **WHEN** reorder succeeds
- **THEN** exactly one new `TripEditEvent` with `edit_type=reorder` exists for that trip_id for the attempt

#### Scenario: Stale second edit writes no audit row
- **WHEN** the flag is true and a second edit sends the version from before the first edit committed
- **THEN** the response is 409 and the `TripEditEvent` count increased only for the first edit

### Requirement: Step 7.4 verification gate for edit/replan behavior

The P7 day-edit behavior contract in this capability MUST be proven by `tests/trips/test_edit_replan.py` (step **7.4** in `docs/steps/step7.md`), not only by thin 7.3 HTTP smoke. That suite MUST exercise FakeRoutingProvider-backed service and thin HTTP cases covering reorder/remove/add/reoptimize success and failure paths, ownership 403, rate-limit 429, preserve-order / morning-slot asymmetry, dropped_stops rollback, single `TripEditEvent` on success, zero audit rows on validation failure, and mutated-day-only RoutingProvider calls. Claiming the HTTP + service edit surface complete without this suite green is forbidden.

#### Scenario: Behavior contract verified by edit/replan suite

- **WHEN** step 7.4 validation runs
- **THEN** `python -m pytest tests/trips/test_edit_replan.py -v` is green and covers the locked scenario matrix before advancing to 7.5

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
