## MODIFIED Requirements

### Requirement: TripService save_from_state Unit of Work
The system SHALL implement `TripService.save_from_state(state, user_id, session_id, run_id=None) -> Trip | None` that, in one transaction: creates the Trip, inserts all TripPlace rows from `state["schedule"]` day dicts, commits on success, and rolls back on any failure (no orphan Trip). Mapping MUST follow the locked v2 map: preferences from interests/budget/include_* **and**, when present and coercible, `base_lat`/`base_lng` from state into preferences; status COMPLETE/FAILED/DRAFT per plan_complete/abort_triggered; each stop’s `leg_polyline` → `TripPlace.polyline`. Return `None` when schedule is empty or the generation is clarification-only with nothing usable. `TripService` MUST NOT call `PlannerService`.

When `run_id` is omitted, the save MUST NOT read or write a planner run. When `run_id` is set and that run already has a trip id, the save MUST return that trip and MUST NOT insert another trip. When `run_id` is set and the run has no trip id, the same transaction that inserts the trip MUST store that trip id on the run before commit. The status change on that run MUST go through the run lifecycle service.

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

#### Scenario: Save without a run leaves runs untouched
- **WHEN** `save_from_state` is called without a run id
- **THEN** no planner run is inserted or updated

#### Scenario: Second save for a run returns the first trip
- **WHEN** `save_from_state` is called with a run id that already has a trip id
- **THEN** the existing trip is returned and no second trip is inserted

#### Scenario: Trip id is committed on the run
- **WHEN** `save_from_state` inserts a trip for a run that had no trip id
- **THEN** after the method returns, the run's stored trip id is that trip
