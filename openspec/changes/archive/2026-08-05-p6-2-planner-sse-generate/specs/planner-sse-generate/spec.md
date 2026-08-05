## ADDED Requirements

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

Settings MUST include `PLANNER_ABSOLUTE_MIN_PLACES` (default 10) and `PLANNER_CACHE_TTL_SECONDS` (default 3600). Step 6.2 MAY call a cache lookup helper that always misses; real cache hit/set is out of scope until 6.4.

Rate limiting for this path MUST continue to use the existing middleware path table (do not add a second limiter in the router).

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

### Requirement: Cache miss stub until Redis backends
Until step 6.4, `maybe_get_cached_state` MUST return `None` (always miss) so the router always takes the fresh `PlannerService.generate` path. The helper MUST exist so 6.4 can wire `CacheBackend` without rewriting the SSE loop.

#### Scenario: Six-two always generates fresh
- **WHEN** generate is called twice with identical PlanRequest bodies in step 6.2
- **THEN** both invocations run `PlannerService.generate` (no cache-hit replay)
