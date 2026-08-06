## ADDED Requirements

### Requirement: Trip edit domain exceptions and input schemas

`src/trips/exceptions.py` MUST define:
- `TripEditValidationError` — HTTP 422, default code `trip_edit_validation_failed`, optional `details` dict (trip unchanged).
- `TripStopConflictError` — HTTP 409, code `stop_already_on_trip`.
- `TripStopNotFoundError` — HTTP 404, code `stop_not_found_on_day`.

`src/trips/schemas.py` MUST define `ReorderStopsIn(place_ids: list[UUID])` and `AddStopIn(place_id: UUID)` for 7.3 route reuse. This step MUST NOT register FastAPI edit routes.

#### Scenario: Validation error carries 422 status metadata

- **WHEN** `TripEditValidationError` is constructed with a message and details
- **THEN** it exposes `status_code=422` and the provided `details`

#### Scenario: Schemas accept UUID lists/ids

- **WHEN** `ReorderStopsIn` / `AddStopIn` are validated with UUID inputs
- **THEN** parsing succeeds without requiring HTTP

### Requirement: TripRepository flush-only day-edit helpers

`TripRepository` MUST provide flush-only helpers (no commit) sufficient for day surgery: hard-delete `TripPlace` by `(trip_id, place_id, day)` (TripPlace has no SoftDeleteMixin), update order/times/polyline fields for a day’s stops, and **sole** insert of `TripEditEvent` rows. Service MUST NOT insert `TripEditEvent` via raw session add outside the repository helper.

#### Scenario: Edit event insert is flush-only

- **WHEN** `insert_edit_event` (or equivalent) is called
- **THEN** a `TripEditEvent` is flushed and the session is not committed by the repository

### Requirement: TripService day-surgery helpers and UoW

`TripService` MUST implement private helpers per `docs/steps/step7.md` §7.2: `_hydrate_scored` (Place → `ScoredPlace` with `score=1.0`, coords via `to_shape`), `_snapshot_day` (before payload), `_fixed_order_day` (matrix once + consecutive legs + `populate_leg_polylines`; MUST NOT call `optimize_route`), `_optimize_day` (delegates to `optimize_route`), `_schedule_mutated_day` (`preserve_order` only for reorder), `_validate_full_trip` (mutated day from new plan; other days from stored TripPlace fields only — zero RoutingProvider calls for unchanged days; REORDER downgrades `morning_slot_violation*` errors to warnings), and `_persist_day_and_audit` (single commit: TripPlace mutations with `leg_polylines` zipped onto `TripPlace.polyline`, one `TripEditEvent`, `mark_trip_edited`, then reload). MUST NOT invent `ScheduledStop.leg_polyline` / `DayPlan.day_polyline`. Concurrency MUST be documented as last-write-wins (no row locking). Default routing MUST be injectable `OsrmRoutingProvider` (or constructor/`routing=` override for tests). Edit path MUST NOT import PlannerService, `execute_tool`, LangGraph, or LLM clients.

#### Scenario: Fixed-order path skips optimize

- **WHEN** `_fixed_order_day` runs for a caller-chosen order
- **THEN** `optimize_route` is not called and polylines come from `populate_leg_polylines`

#### Scenario: Unchanged days skip routing during validate

- **WHEN** `_validate_full_trip` validates a multi-day trip after mutating one day
- **THEN** no RoutingProvider calls are made for the non-mutated days

#### Scenario: Validation failure leaves no audit row

- **WHEN** remaining validation errors cause `TripEditValidationError` before commit
- **THEN** the transaction rolls back and no new `TripEditEvent` exists

## MODIFIED Requirements

### Requirement: TripService day-edit operations surface

`TripService` SHALL expose owner-checked methods `reorder_stops`, `remove_stop`, `add_stop`, and `reoptimize_day` that perform day surgery via `travel_engine` + injected `RoutingProvider`, validate, persist TripPlaces + one `TripEditEvent`, call `EvaluationService.mark_trip_edited`, and commit in one UoW — per `p7-trip-edit-replan` / `docs/steps/step7.md` v2.1. Domain exceptions MUST include `TripEditValidationError` (422), `TripStopConflictError` (409), and `TripStopNotFoundError` (404 `stop_not_found_on_day`).

Semantics:
- Common preamble: load trip with places (404 if missing); `trip.user_id != user_id` → `TripForbiddenError`; resolve destination + `_resolve_base`; snapshot day **before** mutation; filter `day_number == day`. Add onto empty day is allowed; remove that would empty is not.
- **reorder_stops:** require `len(place_ids)==len(current)` and `set(place_ids)==set(current)` else 422; `_fixed_order_day` → schedule `preserve_order=True` → validate with REORDER morning downgrade → persist; `EditType.REORDER`. MUST NOT call `optimize_route`.
- **remove_stop:** not on day → `TripStopNotFoundError`; sole stop → 422 `day_would_be_empty`; else `optimize_route`; non-empty `dropped_stops` → 422 `edit_would_drop_other_stops`; default schedule → validate → persist; `EditType.REMOVE_STOP`.
- **add_stop:** missing Place → 404; wrong destination → 422; already on trip → 409; append → `optimize_route`; non-empty `dropped_stops` → 422 with details; default schedule → validate → persist; `EditType.ADD_STOP`.
- **reoptimize_day:** `optimize_route`; same dropped_stops 422 rule; default schedule → validate → persist; `EditType.REOPTIMIZE_DAY`.

Still-over-budget with empty `dropped_stops` MUST still fail via travel-cap validation → 422. This step MUST NOT register HTTP routes.

#### Scenario: Edit methods exist on TripService

- **WHEN** `TripService` is inspected after step 7.2
- **THEN** it defines `reorder_stops`, `remove_stop`, `add_stop`, and `reoptimize_day`

#### Scenario: Reorder preserves client order and writes polylines

- **WHEN** `reorder_stops` is called with a valid permutation under a Fake routing provider
- **THEN** persisted `order_in_day` matches the permutation, schedule used preserve-order, and `TripPlace.polyline` values reflect `populate_leg_polylines` output

#### Scenario: Remove last stop rejected

- **WHEN** `remove_stop` is called for the only stop on a day
- **THEN** `TripEditValidationError` with code `day_would_be_empty` is raised and the stop remains

#### Scenario: Add duplicate rejected

- **WHEN** `add_stop` is called for a place already on the trip
- **THEN** `TripStopConflictError` (409) is raised and zero TripPlace rows change

#### Scenario: Add that would drop other stops is rejected

- **WHEN** `add_stop` causes `optimize_route` to return non-empty `dropped_stops`
- **THEN** `TripEditValidationError` with code `edit_would_drop_other_stops` is raised and zero TripPlace rows / edit events change
