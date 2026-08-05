## MODIFIED Requirements

### Requirement: Trip persistence with Unit of Work and guest ownership
The system MUST implement `TripRepository` and `TripService.save_from_state(state, user_id, session_id) → Trip | None` such that Trip + TripPlace rows are written in **one transaction**. Partial TripPlace failure MUST roll back the entire save (no Trip without its places). Field mapping MUST follow the v2 locked mapping (including `TripPlace.polyline` from `leg_polyline`). Empty clarification/abort with no usable schedule MUST NOT create a Trip row (`None`).

Unauthenticated access to a trip MUST require the `wandr_session` cookie to **exactly match** `Trip.session_id`; mismatch or missing cookie MUST return **403** (same class of failure as an authenticated user accessing another user’s trip). Guests with matching session MAY access trips where `user_id IS NULL` prior to claim. Step **6.1** delivered the service/repository/schemas/exceptions surface (`save_from_state`, `assert_can_access`, `claim_for_user`) unit-testable with a DB session.

The system MUST implement `TripService.claim_for_user(trip, user_id, session_id)`. `POST /api/v1/trips/{id}/claim` (`require_auth`) MUST be registered in step **6.3**: succeed only when `trip.user_id IS NULL` and session matches; otherwise **403** (session) or **409** (`TripAlreadyClaimedError`). Step **6.3** MUST also register trips list/get/geojson/delete HTTP per the locked auth matrix.

#### Scenario: Save then reload includes all stops
- **WHEN** `save_from_state` is called with a complete itinerary state
- **THEN** a Trip is returned and `get_with_places` returns every persisted stop

#### Scenario: Guest session mismatch is forbidden
- **WHEN** an unauthenticated client requests a trip whose `session_id` does not match `wandr_session`
- **THEN** the API returns HTTP 403 (not 404)

#### Scenario: Partial insert rolls back
- **WHEN** a TripPlace insert fails mid-save
- **THEN** no Trip row remains committed for that attempt

#### Scenario: Claim after login (service)
- **WHEN** `claim_for_user` is called with matching session on an unclaimed trip
- **THEN** `trip.user_id` equals that user after commit

#### Scenario: Re-claim is conflict
- **WHEN** claim is attempted on a trip that already has `user_id` set
- **THEN** `TripAlreadyClaimedError` is raised (HTTP 409 via the 6.3 claim route)

#### Scenario: Step 6.3 registers trips HTTP including claim
- **WHEN** step 6.3 validation runs after the trips router lands
- **THEN** trips CRUD, geojson, and claim routes are registered on the app

### Requirement: Planner generate SSE HTTP endpoint with pre-graph floor
The system MUST expose `POST /api/v1/planner/generate` accepting `PlanRequest(destination_id, raw_input, days?, base_lat?, base_lng?, accommodation_label?)` and returning `StreamingResponse` with `content-type: text/event-stream` and headers including `Cache-Control: no-cache` and `X-Accel-Buffering: no`.

SSE event names MUST include at least: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `clarification_needed`, `error`.

The endpoint MUST use `optional_auth`. Omitted `base_lat`/`base_lng` MUST default to the destination center. If destination `place_count < PLANNER_ABSOLUTE_MIN_PLACES`, the endpoint MUST return HTTP **409** with code `destination_not_ready` and MUST NOT invoke the planner graph or cache lookup.

SSE design MUST run generation as a background task; `on_event` pushes into an `asyncio.Queue`; the generator yields **non-terminal** events while the graph runs using `asyncio.wait_for(queue.get(), timeout=1.0)`; terminal events (`itinerary_done` / `error` / `clarification_needed`) MUST be buffered until the task completes; for usable `itinerary_done`, the router MUST call `save_from_state` then yield **exactly one** terminal frame enriched with `trip_id` when a Trip was saved. `request.is_disconnected()` MUST cancel the background task. Timeout/disconnect MUST close cleanly — never hang and never await-full-invoke-then-dump.

`PlannerService` MUST remain free of FastAPI `Request`/`StreamingResponse` types; the router is the SSE adapter over `generate(..., on_event=...)`.

Step **6.2** delivered this HTTP SSE endpoint, settings keys `PLANNER_ABSOLUTE_MIN_PLACES` and `PLANNER_CACHE_TTL_SECONDS`, and a cache-lookup helper that may always miss. Real cache hit/set and Redis backends remain step **6.4**. Trips CRUD/GeoJSON/claim HTTP are delivered in step **6.3**.

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

#### Scenario: Step 6.2 registered generate before trips HTTP
- **WHEN** step 6.2 validation ran after the planner router landed (historical gate)
- **THEN** `planner/generate` was registered while trips claim/CRUD routes were still unregistered until 6.3

### Requirement: Trips CRUD and GeoJSON
The system MUST expose:
- `GET /api/v1/trips` → `PaginatedResponse[TripOut]` with `require_auth`
- `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` with `optional_auth` + ownership
- `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (public; not wrapped in `ApiResponse`)
- `DELETE /api/v1/trips/{id}` → 204 with `require_auth` + ownership
- `POST /api/v1/trips/{id}/claim` → `ApiResponse[TripOut]` with `require_auth` + session match + unclaimed

GeoJSON MUST be built from persisted trip data via `TripService.build_geojson` (no live OSRM on read) and MUST include LineString features when polylines decode successfully; all-None polylines MUST still yield valid Point features. Accessing another user’s trip or guest session mismatch MUST return **403**. Anonymous DELETE is forbidden by design. Step **6.3** MUST deliver this HTTP surface.

#### Scenario: GeoJSON is map-renderable
- **WHEN** `GET /api/v1/trips/{id}/geojson` is called for a saved trip with polylines/coords
- **THEN** the body is a valid GeoJSON FeatureCollection suitable for geojson.io and includes at least one LineString when polylines were persisted

#### Scenario: List requires auth
- **WHEN** an unauthenticated client calls `GET /api/v1/trips`
- **THEN** the API returns 401

#### Scenario: Claim HTTP restored
- **WHEN** an authenticated owner session claims an unclaimed trip
- **THEN** the API returns 200 with `TripOut.user_id` set; wrong session → 403; re-claim → 409
