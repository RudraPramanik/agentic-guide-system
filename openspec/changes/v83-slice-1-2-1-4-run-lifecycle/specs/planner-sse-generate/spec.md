## MODIFIED Requirements

### Requirement: POST generate streams SSE with terminal buffering
The system MUST register `POST /api/v1/planner/generate` under prefix `/api/v1/planner` returning `StreamingResponse` with media type `text/event-stream` and response headers including `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and `Connection: keep-alive`. Auth MUST be `optional_auth`. Omitted `base_lat`/`base_lng` MUST default to the destination center.

SSE event names MUST include at least: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `clarification_needed`, `error`. Tracking MUST NOT add, remove, or rename those event names.

Generation MUST run as a background task. `on_event` MUST enqueue `(event, data)` into an `asyncio.Queue`. The generator MUST yield non-terminal events while running, using `asyncio.wait_for(queue.get(), timeout=1.0)`. Terminal events (`itinerary_done`, `error`, `clarification_needed`) MUST be buffered and MUST NOT be yielded until the task completes. For buffered `itinerary_done` with a recoverable final state, the router MUST call `TripService.save_from_state` and enrich the payload with `trip_id` when a Trip is saved, then yield **exactly one** terminal frame. `error` and `clarification_needed` MUST yield without trip save. Client disconnect MUST cancel the background task. The response MUST ensure a `wandr_session` cookie (create if missing).

Settings MUST include `RUN_TRACKING_ENABLED` (default false), `PLANNER_ABSOLUTE_MIN_PLACES` (default 10), and `PLANNER_CACHE_TTL_SECONDS` (default 3600).

While `RUN_TRACKING_ENABLED` is false, generate MUST ignore `Idempotency-Key`, MUST NOT write a planner run, and MUST NOT include `run_id` on any SSE payload. A repeated submit while the flag is off MUST still be allowed to save a new trip.

While `RUN_TRACKING_ENABLED` is true, every yielded SSE data object on that response MUST include `run_id`. A request that matches an existing run for the same owner and idempotency key MUST NOT start the cold generate runner or the cache replay runner. If that run already has a trip, the single terminal event MUST be `itinerary_done` and MUST include that `trip_id`. If that run is terminal and has no trip, the single terminal event MUST be `error` and its code MUST be the stored failure code. If that run is not terminal, the single terminal event MUST be `error` with code `run_in_progress`. These replay paths MUST NOT save a second trip.

On cache hit for a request that does not match an existing run, the background task MUST be `_replay_cached` (not `PlannerService.generate`); on miss, `PlannerService.generate`. Persistence MUST use the same `save_from_state` path for both. After a successful fresh generation suitable for caching, the router (or planner cache helper invoked from the router) MUST best-effort write the cacheable state subset.

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
- **WHEN** `maybe_get_cached_state` returns a usable cached state and the request does not match an existing planner run
- **THEN** the router runs `_replay_cached` and still calls `save_from_state` for buffered `itinerary_done`

#### Scenario: Missing terminal is surfaced as error
- **WHEN** the generate background task finishes with an empty terminal buffer
- **THEN** the client receives exactly one terminal `error` and the connection does not hang waiting for a success frame

#### Scenario: Flag off omits run_id
- **WHEN** a client generates a plan while run tracking is off
- **THEN** SSE event names are unchanged and no payload contains `run_id`

#### Scenario: Flag on adds run_id without a new event name
- **WHEN** a tracked generate runs the cold path or the cache replay
- **THEN** yielded payloads include `run_id` and the event names are from the existing set

#### Scenario: Repeated key does not open a second generation
- **WHEN** a tracked request matches an existing run that already has a trip
- **THEN** the client receives one `itinerary_done` with that trip id and the cold runner and the cache replay do not start
