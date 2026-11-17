## Purpose

Tracks one planner generate as a run with a code-owned status, so a repeated submit returns the same trip and a client can read that run after the stream drops. The table itself comes from subslice 1.1.

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Generate and HTTP stay unchanged
**Reason**: Flag-on generate writes runs, and GET is a real route. Flag-off generate still writes no run and still omits `run_id`.
**Migration**: Archive `v83-slice-1-1-planner-runs` first. Unknown run ids still return 404. Do not keep a requirement that the route is unregistered.
