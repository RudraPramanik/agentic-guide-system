## Purpose

Trip repository and service persistence for P6.1 — exceptions, response schemas, Unit of Work `save_from_state`, ownership policy, and claim helpers. HTTP claim/CRUD/GeoJSON land in P6.3 (`trips-http-crud-geojson`); service helpers remain the policy source of truth.

## Requirements

### Requirement: Trip domain exceptions
The system SHALL implement `src/trips/exceptions.py` with `TripNotFoundError` (HTTP 404 via `NotFoundError`), `TripForbiddenError` (HTTP 403 via `ForbiddenError`), and `TripAlreadyClaimedError` (HTTP 409, `code="trip_already_claimed"`) for claim conflicts. Ownership misses MUST raise `TripForbiddenError`, never `TripNotFoundError`.

#### Scenario: Claim conflict is 409
- **WHEN** `TripAlreadyClaimedError` is raised
- **THEN** its `status_code` is 409 and `code` is `trip_already_claimed`

#### Scenario: Ownership miss is forbidden not not-found
- **WHEN** `assert_can_access` rejects a caller
- **THEN** it raises `TripForbiddenError` (403), not `TripNotFoundError`

### Requirement: Trip response schemas
The system SHALL implement `TripOut` and `TripPlaceOut` in `src/trips/schemas.py` covering existing Trip / TripPlace columns needed by list/get (including `suggested_start_time`, `visit_duration_min`, `polyline`) plus joined Place `lat`/`lng` (via PostGIS `to_shape`, same pattern as `PlaceOut`). Schemas MUST NOT invent columns absent from models.

#### Scenario: TripPlaceOut includes timing and geometry fields
- **WHEN** a `TripPlaceOut` is built from a loaded TripPlace + Place
- **THEN** it exposes `suggested_start_time`, `visit_duration_min`, `polyline`, `lat`, and `lng`

### Requirement: TripRepository list and eager get
The system SHALL implement `TripRepository(BaseRepository[Trip, UUID])` with:
- `list_by_user(user_id, params)` and `list_by_session(session_id, params)` returning paginated non-deleted trips
- `get_with_places(trip_id)` returning the trip with TripPlace rows and related Place eagerly loaded (coords available), or `None` if missing/soft-deleted

Repository writes MUST remain flush-only.

#### Scenario: get_with_places loads stops and place coords
- **WHEN** `get_with_places` is called for a saved trip with stops
- **THEN** the returned trip includes all TripPlace rows and each related Place is available for lat/lng extraction without additional queries per stop

#### Scenario: Soft-deleted trip is not returned
- **WHEN** `get_with_places` is called for a soft-deleted trip id
- **THEN** the result is `None`

### Requirement: TripService save_from_state Unit of Work
The system SHALL implement `TripService.save_from_state(state, user_id, session_id) -> Trip | None` that, in one transaction: creates the Trip, inserts all TripPlace rows from `state["schedule"]` day dicts, commits on success, and rolls back on any failure (no orphan Trip). Mapping MUST follow the locked v2 map: preferences from interests/budget/include_* **and**, when present and coercible, `base_lat`/`base_lng` from state into preferences; status COMPLETE/FAILED/DRAFT per plan_complete/abort_triggered; each stop’s `leg_polyline` → `TripPlace.polyline`. Return `None` when schedule is empty or the generation is clarification-only with nothing usable. `TripService` MUST NOT call `PlannerService`.

#### Scenario: Save then reload includes polylines
- **WHEN** `save_from_state` runs on a complete schedule whose stops include `leg_polyline`
- **THEN** the returned Trip is committed and `get_with_places` returns matching `TripPlace.polyline` values

#### Scenario: Partial insert rolls back
- **WHEN** a TripPlace insert fails mid-save
- **THEN** zero Trip rows remain committed for that attempt

#### Scenario: Clarification-only skips persist
- **WHEN** `save_from_state` is called with an empty schedule and `plan_complete` false / not a usable abort itinerary
- **THEN** the return value is `None` and no Trip row is created

#### Scenario: Base coords land in preferences when present on state
- **WHEN** `save_from_state` runs with numeric `base_lat` and `base_lng` on state
- **THEN** committed `Trip.preferences` include those floats

### Requirement: save_from_state persists base coordinates in preferences

When `state` contains both `base_lat` and `base_lng` values that successfully coerce to `float`, `TripService.save_from_state` MUST store them on `Trip.preferences` as floats alongside existing keys (`interests`, `budget`, `include_offbeat`, `include_trekking`). When either value is missing or not coercible, preferences MUST omit both `base_lat` and `base_lng` (save MUST still succeed). No Alembic migration and no new Trip columns. `TripService` MUST NOT call `PlannerService`.

#### Scenario: Save stores base prefs when present

- **WHEN** `save_from_state` runs with a usable schedule and numeric `base_lat` / `base_lng` on state
- **THEN** the committed trip’s `preferences` include those float values

#### Scenario: Save omits base keys when absent

- **WHEN** `save_from_state` runs without `base_lat` / `base_lng` on state
- **THEN** the trip is saved and `preferences` do not contain `base_lat` or `base_lng`

### Requirement: _resolve_base prefers preferences then destination

`TripService` (or a module-private helper used by it) MUST provide `_resolve_base(trip, destination) -> tuple[float, float]` that returns `(preferences.base_lat, preferences.base_lng)` when both are non-bool `int` or `float`, otherwise `(destination.lat, destination.lng)`. Non-numeric or partial prefs MUST fall back to destination. The helper MUST NOT raise an HTTP 500 / uncaught exception for bad prefs shapes.

#### Scenario: Resolve prefers preferences over destination

- **WHEN** `_resolve_base` is called with numeric prefs base different from destination centroid
- **THEN** the returned coordinates are the preferences values

#### Scenario: Resolve falls back to destination

- **WHEN** prefs lack numeric base keys (missing, non-numeric, or bool)
- **THEN** `_resolve_base` returns `destination.lat` / `destination.lng`

### Requirement: Trip edit domain exceptions and input schemas

`src/trips/exceptions.py` MUST define:
- `TripEditValidationError` — HTTP 422, default code `trip_edit_validation_failed`, optional `details` dict (trip unchanged).
- `TripStopConflictError` — HTTP 409, code `stop_already_on_trip`.
- `TripStopNotFoundError` — HTTP 404, code `stop_not_found_on_day`.

`src/trips/schemas.py` MUST define `ReorderStopsIn(place_ids: list[UUID])` and `AddStopIn(place_id: UUID)` for 7.3 route reuse. Step 7.2 MUST NOT register FastAPI edit routes (those land in 7.3).

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

### Requirement: TripService day-edit operations surface

`TripService` SHALL expose owner-checked methods `reorder_stops`, `remove_stop`, `add_stop`, and `reoptimize_day` that perform day surgery via `travel_engine` + injected `RoutingProvider`, validate, persist TripPlaces + one `TripEditEvent`, call `EvaluationService.mark_trip_edited`, and commit in one UoW — per `p7-trip-edit-replan` / `docs/steps/step7.md` v2.1. Domain exceptions MUST include `TripEditValidationError` (422), `TripStopConflictError` (409), and `TripStopNotFoundError` (404 `stop_not_found_on_day`).

Semantics:
- Common preamble: load trip with places (404 if missing); `trip.user_id != user_id` → `TripForbiddenError`; resolve destination + `_resolve_base`; snapshot day **before** mutation; filter `day_number == day`. Add onto empty day is allowed; remove that would empty is not.
- **reorder_stops:** require `len(place_ids)==len(current)` and `set(place_ids)==set(current)` else 422; `_fixed_order_day` → schedule `preserve_order=True` → validate with REORDER morning downgrade → persist; `EditType.REORDER`. MUST NOT call `optimize_route`.
- **remove_stop:** not on day → `TripStopNotFoundError`; sole stop → 422 `day_would_be_empty`; else `optimize_route`; non-empty `dropped_stops` → 422 `edit_would_drop_other_stops`; default schedule → validate → persist; `EditType.REMOVE_STOP`.
- **add_stop:** missing Place → 404; wrong destination → 422; already on trip → 409; append → `optimize_route`; non-empty `dropped_stops` → 422 with details; default schedule → validate → persist; `EditType.ADD_STOP`.
- **reoptimize_day:** `optimize_route`; same dropped_stops 422 rule; default schedule → validate → persist; `EditType.REOPTIMIZE_DAY`.

Still-over-budget with empty `dropped_stops` MUST still fail via travel-cap validation → 422. Step 7.2 MUST NOT register HTTP routes (7.3).

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

### Requirement: Ownership and claim helpers
The system SHALL implement `TripService.assert_can_access(trip, *, user_id, session_id)` and `TripService.claim_for_user(trip, user_id, session_id) -> Trip`. Guest access requires exact `session_id` match. Authenticated access allows `trip.user_id == user_id` or (pre-claim) `trip.user_id is None` with matching session. Claim succeeds only when `trip.user_id is None` and session matches; otherwise `TripForbiddenError` or `TripAlreadyClaimedError`. Claim commits the updated `user_id`. HTTP claim and CRUD routes are delivered in step **6.3** (`trips-http-crud-geojson`); these service helpers remain the policy source of truth.

#### Scenario: Guest matching session may access unclaimed trip
- **WHEN** `user_id` is None and `session_id` equals `trip.session_id` on an unclaimed trip
- **THEN** `assert_can_access` returns without error

#### Scenario: Claim with matching session
- **WHEN** `claim_for_user` is called with matching session on `trip.user_id is None`
- **THEN** the trip’s `user_id` is set, committed, and returned

#### Scenario: Claim wrong session
- **WHEN** `claim_for_user` is called with a mismatched session
- **THEN** `TripForbiddenError` is raised and `trip.user_id` remains unchanged

#### Scenario: Re-claim conflict
- **WHEN** `claim_for_user` is called on a trip that already has `user_id` set
- **THEN** `TripAlreadyClaimedError` is raised

### Requirement: build_geojson from loaded trip
The system SHALL implement `TripService.build_geojson(trip) -> dict` that accepts a trip already loaded with places (and Place coords) and returns a GeoJSON FeatureCollection. It MUST emit Point features for stops and LineString features when `TripPlace.polyline` values decode; it MUST NOT perform network I/O or call `PlannerService`. Undecodable or None polylines MUST degrade to Points-only for affected legs/days without raising.

#### Scenario: Build includes Points
- **WHEN** `build_geojson` is called with a trip that has stops with Place coords
- **THEN** the FeatureCollection contains a Point feature per stop

#### Scenario: Build includes LineString when polyline present
- **WHEN** stops include decodable `polyline` values
- **THEN** the FeatureCollection contains at least one LineString feature

#### Scenario: None polylines do not raise
- **WHEN** all stop polylines are None
- **THEN** `build_geojson` returns a valid FeatureCollection of Points and does not raise

### Requirement: HTTP-facing service helpers
The system SHALL provide thin `TripService` helpers used by the 6.3 router: load-or-404 + ownership check for get/delete, paginated list for the authenticated user, soft-delete with commit, and claim wrapper that loads then calls `claim_for_user`. Repository remains flush-only except where existing BaseRepository soft_delete patterns apply; service owns commit for mutating helpers.

#### Scenario: Get missing trip is 404
- **WHEN** get helper is called for an unknown or soft-deleted trip id
- **THEN** it raises `TripNotFoundError`

#### Scenario: Soft delete commits
- **WHEN** soft-delete helper succeeds for an owned trip
- **THEN** subsequent `get_with_places` returns None for that id
