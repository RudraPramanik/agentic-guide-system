## MODIFIED Requirements

### Requirement: Planner generate SSE HTTP endpoint with pre-graph floor
The system MUST expose `POST /api/v1/planner/generate` accepting `PlanRequest(destination_id, raw_input, days?, base_lat?, base_lng?, accommodation_label?)` and returning `StreamingResponse` with `content-type: text/event-stream` and headers including `Cache-Control: no-cache` and `X-Accel-Buffering: no`.

SSE event names MUST include at least: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `clarification_needed`, `error`.

The endpoint MUST use `optional_auth`. Omitted `base_lat`/`base_lng` MUST default to the destination center. If destination `place_count < PLANNER_ABSOLUTE_MIN_PLACES`, the endpoint MUST return HTTP **409** with code `destination_not_ready` and MUST NOT invoke the planner graph or cache lookup.

SSE design MUST run generation as a background task; `on_event` pushes into an `asyncio.Queue`; the generator yields **non-terminal** events while the graph runs using `asyncio.wait_for(queue.get(), timeout=1.0)`; terminal events (`itinerary_done` / `error` / `clarification_needed`) MUST be buffered until the task completes; for usable `itinerary_done`, the router MUST call `save_from_state` then yield **exactly one** terminal frame enriched with `trip_id` when a Trip was saved. `request.is_disconnected()` MUST cancel the background task. Timeout/disconnect MUST close cleanly — never hang and never await-full-invoke-then-dump.

`PlannerService` MUST remain free of FastAPI `Request`/`StreamingResponse` types; the router is the SSE adapter over `generate(..., on_event=...)`.

Step **6.2** MUST deliver this HTTP SSE endpoint, settings keys `PLANNER_ABSOLUTE_MIN_PLACES` and `PLANNER_CACHE_TTL_SECONDS`, and a cache-lookup helper that may always miss. Real cache hit/set and Redis backends remain step **6.4**. Trips CRUD/GeoJSON/claim HTTP remain step **6.3**.

#### Scenario: Stream emits while generation runs
- **WHEN** a valid plan request is posted for a ready destination
- **THEN** non-terminal SSE events are yielded during generation and exactly one terminal event closes the logical stream

#### Scenario: Terminal frame includes trip_id when saved
- **WHEN** generation completes with a usable itinerary that is auto-saved
- **THEN** the single `itinerary_done` payload includes `trip_id`

#### Scenario: Absolute min places rejects before graph
- **WHEN** destination `place_count` is below `PLANNER_ABSOLUTE_MIN_PLACES`
- **THEN** response is HTTP 409 with `destination_not_ready` and no tool loop runs

#### Scenario: Timeout closes stream cleanly
- **WHEN** generation exceeds `PLANNER_GENERATION_TIMEOUT_SECONDS`
- **THEN** an SSE `error` event is emitted as the terminal frame and the stream closes without hanging

#### Scenario: Disconnect cancels server work
- **WHEN** the client disconnects mid-stream
- **THEN** the background generation task is cancelled (no continued unbounded LLM spend for that request)

#### Scenario: Step 6.2 registers generate without trips HTTP
- **WHEN** step 6.2 validation runs after the planner router lands
- **THEN** `planner/generate` is registered and trips claim/CRUD routes remain unregistered
