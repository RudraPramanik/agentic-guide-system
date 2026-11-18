## Purpose

P6.2–6.4 planner HTTP SSE generate — PlanRequest schema, absolute min-places floor, StreamingResponse adapter over PlannerService with terminal-event buffering, trip save enrichment, and real CacheBackend hit/set (cache hits still persist a new trip).

## Requirements

### Requirement: PlanRequest schema for generate
The system MUST provide `PlanRequest` in `src/planner/schemas.py` with fields:
`destination_id: UUID`, `raw_input: str`, optional `days: int | None`, optional `base_lat` / `base_lng: float | None`, optional `accommodation_label: str | None` (display-only), optional `discovery_anchor`, and optional `radius_km: float | None`.

`discovery_anchor`, when present, MUST carry `canonical_name`, `location_type`, `lat`, `lng`, and `provider` (`nominatim`, `catalog`, or `user`), and MAY carry `query` and `provider_id`. `base_lat` and `base_lng` MUST remain the trip base. They MUST NOT be overwritten from `discovery_anchor`.

A body that omits `discovery_anchor` and `radius_km` MUST still be accepted.

#### Scenario: Schema accepts blueprint PlanRequest fields
- **WHEN** a valid JSON body includes `destination_id`, `raw_input`, and optional `days`, `base_lat`, `base_lng`, `accommodation_label`
- **THEN** FastAPI/Pydantic accepts the body as `PlanRequest`

#### Scenario: An anchor does not replace the trip base
- **WHEN** a body sets `base_lat` and `base_lng` and also sets `discovery_anchor` to a different point
- **THEN** the accepted trip base is the body's `base_lat` and `base_lng`

### Requirement: Flag-off generate ignores the anchor
While `LOCATION_V2_ENABLED` is false, generate MUST ignore `discovery_anchor` and `radius_km`. The idempotency material and the preference-cache key MUST be the same string they are today for the same destination, text, days, and base. The graph state MUST NOT carry a search area. SSE event names MUST stay the same, and `itinerary_done` MUST NOT gain an anchor field.

#### Scenario: A legacy body is unchanged with the flag off
- **WHEN** the flag is false and the body has no anchor
- **THEN** generate follows the current destination and base path and does not call the location library

#### Scenario: A posted anchor is ignored with the flag off
- **WHEN** the flag is false and the body includes `discovery_anchor` and `radius_km`
- **THEN** the idempotency material matches the material for that body with those fields omitted, and no search area is stored

### Requirement: Flag-on generate builds one server-owned search area
While `LOCATION_V2_ENABLED` is true, generate MUST build one search area before the graph and MUST pass that area into retrieval. The area stored on the trip MUST be this server-built area. A client polygon MUST NOT be stored.

When `discovery_anchor` is absent, the anchor MUST be the destination center with location type `city` and provider `catalog`, and the area MUST be the disclosed city fallback of `LOCATION_CITY_FALLBACK_RADIUS_KM` with `fallback_used` true. Generate MUST NOT geocode that destination again and MUST NOT use a 30 km radius.

When `provider` is `user` and `location_type` is `map_pin`, generate MUST NOT call the geocoder. The radius MUST be the posted `radius_km` after clamping to `LOCATION_MAX_RADIUS_KM`, or `LOCATION_POI_RADIUS_KM` with `fallback_used` true when `radius_km` is omitted.

When `provider` is `nominatim` or `catalog`, generate MUST search `query` when present and `canonical_name` otherwise, and MUST select only the candidate with that provider and provider id. If that candidate is missing, generate MUST fail HTTP 422 with code `anchor_not_confirmed` before the graph and MUST NOT select another candidate. If the confirmed type is `country` or `region`, generate MUST fail HTTP 422 with code `oversized_admin` before the graph and MUST NOT start an LLM call. Latitude or longitude out of range MUST be HTTP 422 with code `invalid_coordinates` before the graph.

A confirmed city or neighborhood that has a boundary MUST keep that boundary. A posted `radius_km` MUST NOT replace it. A confirmed radius strategy MUST use a posted `radius_km` after the same clamp. The description MUST state a clamp when one happens.

Omitted `base_lat` and `base_lng` MUST still default to the destination center. When the flag is true and an anchor or a radius is present, the idempotency material and the preference-cache key MUST include that anchor identity and radius so two areas do not share a cached trip. When both are absent, those strings MUST match the legacy material for the same destination, text, days, and base.

SSE event names MUST stay the same. The anchor MUST be readable from the saved trip, not from a new `itinerary_done` field.

#### Scenario: A destination-only body uses the disclosed city fallback
- **WHEN** the flag is true and the body has a destination id and no discovery anchor
- **THEN** the stored search area uses strategy `radius`, the city fallback radius, and `fallback_used` true, and the radius is not 30

#### Scenario: A map pin does not move the trip base
- **WHEN** the flag is true, `base_lat` and `base_lng` are the destination center, and the anchor is a map pin elsewhere
- **THEN** retrieval is constrained to the pin area and the stored trip base remains the destination center

#### Scenario: An unconfirmed candidate does not start the graph
- **WHEN** the flag is true and the posted provider id is not in the fresh candidate list
- **THEN** the response is HTTP 422 with code `anchor_not_confirmed` and no planner graph runs

#### Scenario: A country anchor does not start the graph
- **WHEN** the confirmed location type is `country` or `region`
- **THEN** the response is HTTP 422 with code `oversized_admin` and no LLM call runs

#### Scenario: Two radii do not share a cache entry
- **WHEN** the flag is true and two bodies differ only in `radius_km`
- **THEN** they do not resolve to the same preference-cache entry

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
