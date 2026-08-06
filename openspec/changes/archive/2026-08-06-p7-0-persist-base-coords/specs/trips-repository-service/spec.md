## ADDED Requirements

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

## MODIFIED Requirements

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
