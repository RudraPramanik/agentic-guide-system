## MODIFIED Requirements

### Requirement: TripService day-surgery helpers and UoW

`TripService` MUST implement private helpers per `docs/steps/step7.md` §7.2: `_hydrate_scored` (Place → `ScoredPlace` with `score=1.0`, coords via `to_shape`), `_snapshot_day` (before payload), `_fixed_order_day` (matrix once + consecutive legs + `populate_leg_polylines`; MUST NOT call `optimize_route`), `_optimize_day` (delegates to `optimize_route`), `_schedule_mutated_day` (`preserve_order` only for reorder), `_validate_full_trip` (mutated day from new plan; other days from stored TripPlace fields only — zero RoutingProvider calls for unchanged days; REORDER downgrades `morning_slot_violation*` errors to warnings), and `_persist_day_and_audit` (single commit: TripPlace mutations with `leg_polylines` zipped onto `TripPlace.polyline`, one `TripEditEvent`, `mark_trip_edited`, then reload). MUST NOT invent `ScheduledStop.leg_polyline` / `DayPlan.day_polyline`. Concurrency MUST be documented as last-write-wins (no row locking). Default routing MUST be `get_routing_provider()` (or constructor/`routing=` override for tests). Edit path MUST NOT import PlannerService, `execute_tool`, LangGraph, or LLM clients.

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
