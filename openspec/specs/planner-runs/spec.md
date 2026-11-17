# planner-runs Specification

## Purpose

Stores one planner run per owner and idempotency key so later slices can track status and prevent duplicate trips. This capability is persistence only. It does not generate trips or expose HTTP.

## Requirements

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

### Requirement: Run tracking defaults off
`RUN_TRACKING_ENABLED` MUST default to false. While it is false, generate MUST ignore `Idempotency-Key`, MUST NOT insert or update a planner run, and MUST NOT add `run_id` to any SSE payload. A trip save that is not given a run id MUST NOT insert or update a planner run.

#### Scenario: Flag off generate writes no run
- **WHEN** a client generates a plan while run tracking is off
- **THEN** no planner run row is created and no SSE payload contains `run_id`

#### Scenario: Flag off save writes no run
- **WHEN** a trip is saved without a run id
- **THEN** no planner run row is created

### Requirement: Run status changes only through the lifecycle service
A stored run status MUST change only through the run lifecycle service. The service MUST reject any transition that is not in the legal table and MUST leave the stored status unchanged. A terminal status MUST NOT change. Generate MUST NOT enter `resolving`, `researching`, or `validating`. An LLM response MUST NOT be able to set the status.

Legal transitions:

- `accepted` → `planning`, `resolving`, `failed`, `cancelled`, `timed_out`
- `resolving` → `researching`, `planning`, `failed`, `cancelled`, `timed_out`
- `researching` → `planning`, `failed`, `cancelled`, `timed_out`
- `planning` → `validating`, `completed`, `degraded`, `failed`, `cancelled`, `timed_out`
- `validating` → `completed`, `partial`, `degraded`, `failed`, `cancelled`, `timed_out`

While tracking is on, generate MUST move the run from `accepted` to `planning` before generation work starts, then to exactly one terminal status: `completed`, `degraded`, `failed`, `cancelled`, or `timed_out`.

#### Scenario: Illegal transition is rejected
- **WHEN** a caller asks to move a run from `completed` to `planning`
- **THEN** the request fails and the stored status remains `completed`

#### Scenario: Direct call may use a non-generate edge
- **WHEN** a caller moves a run from `validating` to `partial`
- **THEN** the stored status becomes `partial`

#### Scenario: Generate does not invent location phases
- **WHEN** a tracked generate finishes
- **THEN** the run never stored `resolving`, `researching`, or `validating`

### Requirement: Every tracked generate ends terminal
While tracking is on, every generate outcome MUST leave a terminal status and a stable `failure_code` when the table below names one. A saved trip with no geo fallback and no routing fallback MUST be `completed` with an empty failure code. A saved trip where geo fallback or routing fallback was used MUST be `degraded` with an empty failure code. The run row MUST be committed before generation work starts.

| Outcome | Status | Failure code |
|---|---|---|
| Trip saved, no geo or routing fallback | `completed` | empty |
| Trip saved, geo or routing fallback | `degraded` | empty |
| Clarification, no trip | `failed` | `needs_clarification` |
| Timeout | `timed_out` | `generation_timeout` |
| Recursion limit | `failed` | `graph_recursion_limit` |
| Aborted generate, no trip | `failed` | `generation_aborted` |
| Client disconnect before a terminal status | `cancelled` | `client_disconnect` |
| Provider failure that fails the generate task | `failed` | `llm_unavailable` |
| Generate ends with no terminal event | `failed` | `missing_terminal` |

The first client's SSE event names stay those already defined for generate. Clarification on that first response remains `clarification_needed`. The failure code is the polling fact, not a new event name.

#### Scenario: Timeout is timed out
- **WHEN** a tracked generate exceeds the planner generation timeout
- **THEN** the run status is `timed_out` and the failure code is `generation_timeout`

#### Scenario: Disconnect cancels the run
- **WHEN** the client disconnects before the run is terminal
- **THEN** the run status is `cancelled` and the failure code is `client_disconnect`

#### Scenario: Provider failure fails the run
- **WHEN** the generate task fails because the model provider is unavailable
- **THEN** the run status is `failed` and the failure code is `llm_unavailable`

#### Scenario: Clean save completes
- **WHEN** a tracked generate saves a trip and did not use a geo or routing fallback
- **THEN** the run status is `completed`, the failure code is empty, and `trip_id` is the saved trip

#### Scenario: Fallback save is degraded
- **WHEN** a tracked generate saves a trip after a geo or routing fallback
- **THEN** the run status is `degraded` and `trip_id` is the saved trip

### Requirement: One owner and key selects one run
While tracking is on, the idempotency key MUST be the `Idempotency-Key` header when that header is present and its trimmed length is between 1 and 128 characters. Otherwise the key MUST be a stable digest of the normalized plan request plus the session id. The normalized request MUST include the destination id, whitespace-collapsed raw input, the day count or zero, and the base latitude and longitude rounded to three decimals. It MUST NOT include the accommodation label. The same normalized request and the same session MUST produce the same fallback key. A different session MUST produce a different fallback key.

A guest MUST match a run only by session id and key. An authenticated caller MUST match by user id and key first. If that misses, the caller MUST match a session-id row only when that row's user id is empty or equal to the caller. A row owned by a different user MUST NOT be returned. The first insert MUST store `input_hash` for the normalized request and MUST NOT change it when the same key is sent again with a different body.

A second insert for the same session and key, or the same user and key, MUST NOT create a second run. The losing attempt MUST use the run that won.

#### Scenario: Header is the key
- **WHEN** a tracked generate sends `Idempotency-Key` within 128 characters
- **THEN** the stored key is that header value

#### Scenario: Missing header uses the session digest
- **WHEN** the same guest sends the same plan body twice with no idempotency header
- **THEN** both requests resolve the same key and the same run

#### Scenario: Two guests do not share a fallback key
- **WHEN** two different sessions send the same plan body with no idempotency header
- **THEN** each session gets its own run

#### Scenario: Over-long header falls back
- **WHEN** a tracked generate sends an `Idempotency-Key` longer than 128 characters
- **THEN** the request still generates and the stored key is the fallback digest, not the header

#### Scenario: Authenticated caller does not read another user's run
- **WHEN** a logged-in user sends a key that belongs to a different user
- **THEN** that other user's run is not returned

#### Scenario: Concurrent inserts leave one run
- **WHEN** two tracked requests with the same new key are inserted together
- **THEN** one run row exists and both requests observe that row

### Requirement: The same key returns the same trip
While tracking is on, a request whose owner and key match an existing run MUST NOT start another generation. If that run is not terminal, the response MUST be a single SSE `error` with code `run_in_progress` and MUST include `run_id`, and MUST NOT save a trip. If that run is terminal and has a trip, the response MUST be a single SSE `itinerary_done` that includes that `trip_id` and `run_id`, and MUST NOT save another trip. If that run is terminal and has no trip, the response MUST be a single SSE `error` whose code is the stored failure code, and MUST include `run_id`. A repeated key with a different plan body MUST return the original run and MUST NOT start a generation for the new body.

A new key MUST still be allowed to use the preference cache. That cache hit MUST save a new trip, as it does today.

#### Scenario: Double submit saves one trip
- **WHEN** two tracked requests use the same key and the first request saves a trip
- **THEN** exactly one trip exists for that run and the second response's `itinerary_done` carries that trip id

#### Scenario: In-progress duplicate does not generate
- **WHEN** a second tracked request arrives while the first run is still `planning`
- **THEN** the second response is one `error` with code `run_in_progress` and no second generation starts

#### Scenario: Different body reuses the run
- **WHEN** a client sends the same key with a different plan body after the first run exists
- **THEN** the original run is returned and no new run is created

#### Scenario: New key still saves on a cache hit
- **WHEN** a tracked request uses a new key and the preference cache has a usable plan
- **THEN** a new trip is saved and a new run points at that trip

### Requirement: Saved trip is visible on the run before the stream finishes
While tracking is on, the trip id MUST be stored on the run in the same commit that inserts the trip. After that commit, `GET /api/v1/planner/runs/{run_id}` MUST return that `trip_id` even if the terminal SSE frame was never sent.

#### Scenario: Crash after save is retrievable
- **WHEN** a tracked save commits the trip and the run's trip id, and the stream then fails before the terminal frame
- **THEN** a later GET of that run id returns the trip id

### Requirement: GET run uses trip ownership
The system MUST register `GET /api/v1/planner/runs/{run_id}` and return `ApiResponse`. The data MUST include `run_id`, `status`, `failure_code`, `trip_id`, `created_at`, and `updated_at`. It MUST NOT include the idempotency key, the input hash, or the session id. An unknown run id MUST return 404. A known run MUST return 403, not 404, when the caller fails the trip ownership rule: a guest cookie must equal the run session, and an authenticated caller must own the run's user id or match the session when the run has no user id. The flag MUST NOT hide an existing row from an owner.

This route is a real read. It is not a stub.

#### Scenario: Owner receives the envelope
- **WHEN** the owning guest or user requests their run
- **THEN** the response is 200 `ApiResponse` and the data status, failure code, and trip id match the stored run

#### Scenario: Wrong session is forbidden
- **WHEN** a guest sends a different session cookie for an existing run
- **THEN** the response is 403 and not 404

#### Scenario: Unknown run is not found
- **WHEN** a client requests a run id that does not exist
- **THEN** the response is 404

#### Scenario: Response hides the key
- **WHEN** an owner reads a run
- **THEN** the body does not contain the idempotency key, the input hash, or the session id
