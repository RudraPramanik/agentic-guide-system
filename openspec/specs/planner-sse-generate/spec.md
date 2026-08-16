## Purpose

P6.2–6.4 planner HTTP SSE generate — PlanRequest schema, absolute min-places floor, StreamingResponse adapter over PlannerService with terminal-event buffering, trip save enrichment, and real CacheBackend hit/set (cache hits still persist a new trip).

## Requirements

### Requirement: PlanRequest schema for generate
The system MUST provide `PlanRequest` in `src/planner/schemas.py` with fields:
`destination_id: UUID`, `raw_input: str`, optional `days: int | None`, optional `base_lat` / `base_lng: float | None`, and optional `accommodation_label: str | None` (display-only).

#### Scenario: Schema accepts blueprint PlanRequest fields
- **WHEN** a valid JSON body includes `destination_id`, `raw_input`, and optional `days`, `base_lat`, `base_lng`, `accommodation_label`
- **THEN** FastAPI/Pydantic accepts the body as `PlanRequest`

### Requirement: Destination not ready floor before graph
The system MUST expose `DestinationNotReadyError` (HTTP 409, code `destination_not_ready`) including `place_count` in details. `POST /api/v1/planner/generate` MUST load the destination via `DestinationService.get_by_id` and, if `place_count < PLANNER_ABSOLUTE_MIN_PLACES` from settings, raise that error **before** starting the planner graph or performing a cache lookup. Missing destination MUST remain 404 via existing `DestinationNotFoundError`.

#### Scenario: Absolute min places rejects before graph
- **WHEN** destination `place_count` is below `PLANNER_ABSOLUTE_MIN_PLACES`
- **THEN** response is HTTP 409 with `destination_not_ready` and no tool loop / generate task runs

#### Scenario: Missing destination is 404
- **WHEN** `destination_id` does not exist
- **THEN** response is HTTP 404 and no generate task runs

### Requirement: POST generate streams SSE with terminal buffering
The system MUST register `POST /api/v1/planner/generate` under prefix `/api/v1/planner` returning `StreamingResponse` with media type `text/event-stream` and response headers including `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and `Connection: keep-alive`. Auth MUST be `optional_auth`. Omitted `base_lat`/`base_lng` MUST default to the destination center.

SSE event names MUST include at least: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `clarification_needed`, `error`.

Generation MUST run as a background task. `on_event` MUST enqueue `(event, data)` into an `asyncio.Queue`. The generator MUST yield non-terminal events while running, using `asyncio.wait_for(queue.get(), timeout=1.0)`. Terminal events (`itinerary_done`, `error`, `clarification_needed`) MUST be buffered and MUST NOT be yielded until the task completes. For buffered `itinerary_done` with a recoverable final state, the router MUST call `TripService.save_from_state` and enrich the payload with `trip_id` when a Trip is saved, then yield **exactly one** terminal frame. `error` and `clarification_needed` MUST yield without trip save. Client disconnect MUST cancel the background task. The response MUST ensure a `wandr_session` cookie (create if missing).

Settings MUST include `PLANNER_ABSOLUTE_MIN_PLACES` (default 10) and `PLANNER_CACHE_TTL_SECONDS` (default 3600).

On cache hit, the background task MUST be `_replay_cached` (not `PlannerService.generate`); on miss, `PlannerService.generate`. Persistence MUST use the same `save_from_state` path for both. After a successful fresh generation suitable for caching, the router (or planner cache helper invoked from the router) MUST best-effort write the cacheable state subset.

Rate limiting for this path MUST continue to use the existing middleware path table (do not add a second limiter in the router).

If the background task completes without having enqueued any terminal event, the router MUST treat that as a server defect: it MUST NOT hang, and MUST yield a single terminal `error` (stable code) rather than closing the stream with only progress frames.

#### Scenario: Route is registered
- **WHEN** the FastAPI app is created
- **THEN** a route path containing `planner/generate` is present

#### Scenario: Stream emits while generation runs
- **WHEN** a valid plan request is posted for a ready destination
- **THEN** non-terminal SSE events are yielded during generation and exactly one terminal event closes the logical stream

#### Scenario: Terminal frame includes trip_id when saved
- **WHEN** generation completes with a usable itinerary that `save_from_state` persists
- **THEN** the single `itinerary_done` payload includes `trip_id`

#### Scenario: Unrecoverable itinerary_done yields one frame without trip_id
- **WHEN** the background task emits `itinerary_done` but final state is unrecoverable (task exception)
- **THEN** the client receives exactly one terminal frame and it has no `trip_id`

#### Scenario: Disconnect cancels server work
- **WHEN** the client disconnects mid-stream
- **THEN** the background generation task is cancelled

#### Scenario: Proxy streaming headers present
- **WHEN** a generate response is returned
- **THEN** headers include `Cache-Control: no-cache` and `X-Accel-Buffering: no`

#### Scenario: Cache hit still persists via same save path
- **WHEN** `maybe_get_cached_state` returns a usable cached state
- **THEN** the router runs `_replay_cached` and still calls `save_from_state` for buffered `itinerary_done`

#### Scenario: Missing terminal is surfaced as error
- **WHEN** the generate background task finishes with an empty terminal buffer
- **THEN** the client receives exactly one terminal `error` and the connection does not hang waiting for a success frame

### Requirement: Live generate emits exactly one terminal from final state
After a non-cache `PlannerService.generate` (or equivalent cold-path runner) finishes — success, clarification, hard abort, timeout, or recursion — the emit bridge MUST publish exactly one terminal SSE event before returning, chosen by locked precedence:

1. If the run already emitted a terminal `error` for timeout or `graph_recursion_limit`, MUST NOT emit a second terminal.
2. Else if `needs_clarification` is true → `clarification_needed` with a non-empty question string (from `clarification_question` or a safe default).
3. Else if the final state is usable for trip persistence (`plan_complete` and a non-empty schedule/itinerary suitable for `save_from_state`) → `itinerary_done` with at least itinerary/days fields the router can enrich.
4. Else → `error` with a stable `code` (for example `generation_aborted` or an existing abort code) so the client always sees a terminal.

Cache replay (`_replay_cached`) MUST continue to emit `itinerary_done` as today. The HTTP router MUST keep buffering terminals and calling `save_from_state` only for `itinerary_done`.

#### Scenario: Successful cold generate yields itinerary_done
- **WHEN** a cold generate completes with `plan_complete` and a usable schedule
- **THEN** the SSE stream includes exactly one terminal `itinerary_done` and, when `save_from_state` persists a trip, that payload includes `trip_id`

#### Scenario: Clarification yields clarification_needed without trip_id
- **WHEN** a cold generate ends with `needs_clarification=true`
- **THEN** the SSE stream’s single terminal is `clarification_needed` with a question, and no trip is saved

#### Scenario: Timeout remains a single error terminal
- **WHEN** generation hits `PLANNER_GENERATION_TIMEOUT_SECONDS`
- **THEN** the stream’s single terminal is `error` with code `generation_timeout` and no duplicate success/clarification terminal follows

### Requirement: Cold-path progress events for FE contract
On a cache miss, the generate path MUST emit `preferences_done` after preferences are resolved (parsed or defaults) and MUST emit `phase_changed` when `agent_phase` transitions. Existing `tool_done` / `tool_batch_done` emits MAY remain. Unknown event names MUST remain ignorable by clients.

#### Scenario: Preferences and phase events appear before terminal on cold path
- **WHEN** a cold generate runs past preference parsing into the tool loop
- **THEN** the stream includes `preferences_done` and at least one `phase_changed` before the terminal event
