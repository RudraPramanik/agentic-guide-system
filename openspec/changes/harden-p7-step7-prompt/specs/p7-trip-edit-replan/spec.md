## ADDED Requirements

### Requirement: Day-scoped edit HTTP API

The system SHALL expose these authenticated endpoints under `/api/v1/trips`:

| Method | Path | Body |
|--------|------|------|
| PATCH | `/{id}/days/{day}/stops/reorder` | `{ "place_ids": [uuid, ...] }` |
| DELETE | `/{id}/days/{day}/stops/{place_id}` | — |
| POST | `/{id}/days/{day}/stops` | `{ "place_id": uuid }` |
| POST | `/{id}/days/{day}/reoptimize` | — |

Each successful response MUST be `ApiResponse[TripOut]`. All four MUST use `require_auth` and ownership (`trip.user_id == caller`); guests MUST NOT edit via session alone (claim first). Ownership miss → 403; missing/soft-deleted trip → 404. Edit routes MUST apply a user-keyed rate-limit dependency (`rate_limit_trip_edit`) in addition to any global middleware default; exceeded limit → 429. Paths MUST NOT be added as broken exact-match UUID entries in `_route_limit_table`.

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

Each successful P7 edit MUST insert **exactly one** `TripEditEvent` created by `TripService`/`TripRepository` (not by EvaluationService), with correct `EditType`, `day_number`, optional `place_id`, and before/after payload, in the same transaction as TripPlace mutations. Concurrent edits to the same trip are last-write-wins (no row locking in P7).

#### Scenario: Successful reorder writes one audit row

- **WHEN** reorder succeeds
- **THEN** exactly one new `TripEditEvent` with `edit_type=reorder` exists for that trip_id for the attempt
