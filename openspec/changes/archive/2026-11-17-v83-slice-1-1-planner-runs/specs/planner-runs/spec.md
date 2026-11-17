## Purpose

Stores one planner run per owner and idempotency key so later slices can track status and prevent duplicate trips. This capability is persistence only. It does not generate trips or expose HTTP.

## ADDED Requirements

### Requirement: Planner run row is additive persistence
The system SHALL store a planner run as its own row, separate from trips. The run's primary key SHALL be the run id. A new row MUST persist `session_id` and `idempotency_key`. `user_id`, `trip_id`, `input_hash`, `failure_code`, `workflow_version`, model name, provider, and fallback reason MUST be stored when provided and MUST be empty when omitted. `created_at` and `updated_at` MUST be set when the row is inserted. The row MUST NOT use a soft-delete timestamp.

#### Scenario: Insert stores the run id and optional facts
- **WHEN** a caller inserts a run with a session id, an idempotency key, and no user, trip, hash, failure code, workflow version, model, provider, or fallback reason
- **THEN** the stored row is readable by its run id, `session_id` and `idempotency_key` match the input, the optional fields are empty, and both timestamps are set

#### Scenario: Insert does not commit the surrounding transaction
- **WHEN** a caller inserts a run and the surrounding transaction rolls back
- **THEN** a later transaction does not see that row

### Requirement: Run status uses the blueprint vocabulary
A stored run status MUST be one of `accepted`, `resolving`, `researching`, `planning`, `validating`, `completed`, `partial`, `degraded`, `failed`, `cancelled`, or `timed_out`. A row inserted without a status MUST be stored as `accepted`. Any other status MUST be rejected.

#### Scenario: Default status is accepted
- **WHEN** a caller inserts a run and omits status
- **THEN** the stored status is `accepted`

#### Scenario: Unknown status is rejected
- **WHEN** a caller inserts a run with status `running`
- **THEN** the insert fails and no row is stored

### Requirement: Owner and idempotency key are unique
The system MUST reject a second run with the same `session_id` and `idempotency_key`. The system MUST reject a second run with the same non-empty `user_id` and `idempotency_key`, including when `session_id` differs. Two runs with the same `idempotency_key`, different `session_id` values, and empty `user_id` MUST both be stored. `session_id` MUST be a non-empty string of at most 64 characters. `idempotency_key` MUST be a non-empty string of at most 128 characters.

#### Scenario: Same session and key is rejected
- **WHEN** two runs are inserted with the same session id and the same idempotency key
- **THEN** the first insert is stored and the second insert fails

#### Scenario: Same key on another session is stored
- **WHEN** two runs are inserted with the same idempotency key, different session ids, and no user id
- **THEN** both rows are stored

#### Scenario: Same user and key is rejected across sessions
- **WHEN** two runs are inserted with the same user id and the same idempotency key and different session ids
- **THEN** the first insert is stored and the second insert fails

### Requirement: Owner and trip references stay non-destructive
`user_id` MUST reference an existing user when it is set. `trip_id` MUST reference an existing trip when it is set. Removing that user or that trip MUST NOT delete the run. The reference MUST become empty instead.

#### Scenario: Unknown user is rejected
- **WHEN** a caller inserts a run whose user id is not an existing user
- **THEN** the insert fails and no row is stored

#### Scenario: Removing the user keeps the run
- **WHEN** a stored run references a user and that user row is deleted
- **THEN** the run remains and its user id is empty

#### Scenario: Removing the trip keeps the run
- **WHEN** a stored run references a trip and that trip row is deleted
- **THEN** the run remains and its trip id is empty

### Requirement: Generate and HTTP stay unchanged
This capability MUST NOT add an HTTP route, MUST NOT change SSE event names, and MUST NOT write a planner run from trip generation. `GET /api/v1/planner/runs/{run_id}` MUST NOT be a registered route.

#### Scenario: Run lookup route is absent
- **WHEN** a client requests `GET /api/v1/planner/runs/{run_id}`
- **THEN** the response is 404

#### Scenario: Saving a trip does not insert a run
- **WHEN** a trip is saved through the existing trip save path
- **THEN** no planner run row is created
