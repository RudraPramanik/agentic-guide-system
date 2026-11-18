## MODIFIED Requirements

### Requirement: TripService day-surgery helpers and UoW

`TripService` MUST implement private helpers per `docs/steps/step7.md` §7.2: `_hydrate_scored` (Place → `ScoredPlace` with `score=1.0`, coords via `to_shape`), `_snapshot_day` (before payload), `_fixed_order_day` (matrix once + consecutive legs + `populate_leg_polylines`; MUST NOT call `optimize_route`), `_optimize_day` (delegates to `optimize_route`), `_schedule_mutated_day` (`preserve_order` only for reorder), `_validate_full_trip` (mutated day from new plan; other days from stored TripPlace fields only — zero RoutingProvider calls for unchanged days; REORDER downgrades `morning_slot_violation*` errors to warnings), and `_persist_day_and_audit` (single commit: TripPlace mutations with `leg_polylines` zipped onto `TripPlace.polyline`, one `TripEditEvent`, `mark_trip_edited`, then reload). MUST NOT invent `ScheduledStop.leg_polyline` / `DayPlan.day_polyline`. Default routing MUST be `get_routing_provider()` (or constructor/`routing=` override for tests). Edit path MUST NOT import PlannerService, `execute_tool`, LangGraph, or LLM clients.

While `CANONICAL_TRIP_V2_ENABLED` is false, concurrency MUST remain last-write-wins with no row locking and no version increment. While the flag is true, `_persist_day_and_audit` MUST increment `trips.version` by 1 in the same transaction as the edit, and a version mismatch raised before mutation MUST roll back with no `TripEditEvent`. Unchanged days reconstructed for validation MUST include only routed statuses (`confirmed`, `user_added`) when the flag is true. Provenance for each rewritten polyline MUST be stored in that same transaction: `osrm` when the polyline is non-null from a non-fallback road route, `haversine_estimate` when the backend produced no polyline because it is the haversine backend, and `none` when a road route was attempted and the polyline is null.

#### Scenario: Fixed-order path skips optimize

- **WHEN** `_fixed_order_day` runs for a caller-chosen order
- **THEN** `optimize_route` is not called and polylines come from `populate_leg_polylines`

#### Scenario: Unchanged days skip routing during validate

- **WHEN** `_validate_full_trip` validates a multi-day trip after mutating one day
- **THEN** no RoutingProvider calls are made for the non-mutated days

#### Scenario: Validation failure leaves no audit row

- **WHEN** remaining validation errors cause `TripEditValidationError` before commit
- **THEN** the transaction rolls back and no new `TripEditEvent` exists

#### Scenario: Default routing uses factory

- **WHEN** `TripService` is constructed without a `routing=` override
- **THEN** its routing adapter is the object returned by `get_routing_provider()`

#### Scenario: Flag off edit does not increment version

- **WHEN** a successful reorder commits while the flag is false
- **THEN** `trips.version` is unchanged

#### Scenario: Flag on edit increments version with the audit row

- **WHEN** a successful reorder commits while the flag is true
- **THEN** `trips.version` is one greater and exactly one new `TripEditEvent` exists for that attempt

## ADDED Requirements

### Requirement: Save writes suggestion rows only when the flag is on
`save_from_state` MUST keep the locked mapping for routed stops, including `leg_polyline` onto `TripPlace.polyline`, in one transaction. When `CANONICAL_TRIP_V2_ENABLED` is true, that same transaction MUST also insert the suggestion rows defined by `canonical-trip-identity` and MUST set each routed stop's `stop_status` to `confirmed` and its `geometry_provenance` from the polyline outcome. When the flag is false, the transaction MUST NOT insert suggestion rows and MUST leave `stop_status` at the server default without putting that key in the JSON. A failure while inserting a suggestion MUST roll back the trip.

#### Scenario: Flag on save commits route and suggestions together
- **WHEN** `save_from_state` runs with the flag true, a usable schedule, and one eligible dropped stop
- **THEN** the committed trip has the routed stops as `confirmed` and that dropped place as `suggested`

#### Scenario: Suggestion insert failure rolls back the trip
- **WHEN** a suggestion insert fails mid-save
- **THEN** zero Trip rows remain committed for that attempt

### Requirement: Trip version conflict is a 409
`src/trips/exceptions.py` MUST define an error with HTTP 409 and code `trip_version_conflict` for a stale `If-Match` or `expected_version`. `ReorderStopsIn` and `AddStopIn` MUST accept an optional `expected_version`. Delete and reoptimize MUST honor `If-Match` because they have no body. The service MUST compare versions before mutating the day.

#### Scenario: Conflict error uses the stable code
- **WHEN** the version conflict error is raised
- **THEN** its status is 409 and its code is `trip_version_conflict`

#### Scenario: Optional expected version parses
- **WHEN** `ReorderStopsIn` is validated with place ids and no `expected_version`
- **THEN** parsing succeeds
