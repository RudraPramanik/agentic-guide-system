## MODIFIED Requirements

### Requirement: POST generate streams SSE with terminal buffering
The system MUST register `POST /api/v1/planner/generate` under prefix `/api/v1/planner` returning `StreamingResponse` with media type `text/event-stream` and response headers including `Cache-Control: no-cache`, `X-Accel-Buffering: no`, and `Connection: keep-alive`. Auth MUST be `optional_auth`. Omitted `base_lat`/`base_lng` MUST default to the destination center.

SSE event names MUST include at least: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `clarification_needed`, `error`.

Generation MUST run as a background task. `on_event` MUST enqueue `(event, data)` into an `asyncio.Queue`. The generator MUST yield non-terminal events while running, using `asyncio.wait_for(queue.get(), timeout=1.0)`. Terminal events (`itinerary_done`, `error`, `clarification_needed`) MUST be buffered and MUST NOT be yielded until the task completes. For buffered `itinerary_done` with a recoverable final state, the router MUST call `TripService.save_from_state` and enrich the payload with `trip_id` when a Trip is saved, then yield **exactly one** terminal frame. `error` and `clarification_needed` MUST yield without trip save. Client disconnect MUST cancel the background task. The response MUST ensure a `wandr_session` cookie (create if missing).

Settings MUST include `PLANNER_ABSOLUTE_MIN_PLACES` (default 10) and `PLANNER_CACHE_TTL_SECONDS` (default 3600).

On cache hit, the background task MUST be `_replay_cached` (not `PlannerService.generate`); on miss, `PlannerService.generate`. Persistence MUST use the same `save_from_state` path for both. After a successful fresh generation suitable for caching, the router (or planner cache helper invoked from the router) MUST best-effort write the cacheable state subset.

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

#### Scenario: Cache hit still persists via same save path
- **WHEN** `maybe_get_cached_state` returns a usable cached state
- **THEN** the router runs `_replay_cached` and still calls `save_from_state` for buffered `itinerary_done`

## REMOVED Requirements

### Requirement: Cache miss stub until Redis backends
**Reason:** Step 6.4 replaces the always-miss stub with real `CacheBackend` lookup/set and `_replay_cached`.
**Migration:** Implement `planner-cache-backend` requirements; keep the same router call sites (`maybe_get_cached_state` / `_replay_cached`).
