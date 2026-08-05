## Purpose

P6 Planner API + Persistence — hardened v2 `docs/steps/step6.md` Cursor build contract (change `harden-p6-planner-api-v2`) and locked behaviors for route geometry hand-off, trips persistence (incl. claim), SSE generate HTTP, trips CRUD/GeoJSON, swappable Redis backends, and ship checklist.

## Requirements

### Requirement: Hardened P6 Cursor prompt exists as step6.md
The project SHALL provide `docs/steps/step6.md` as the sole P6 implementation prompt, modeled on `docs/steps/step5.md` / `docs/steps/step4.md`, adopting the hardened v2 content from `docs/steps/step6_suggestion.md`.

The prompt MUST include:
- Prerequisites (P5 complete — especially `PlannerService.generate` bridge + compiled graph — from `docs/context.md`) and **step 6.0 polyline patch first**
- Prompt conventions and failure standards (`FAILURE BOUNDARY` + `✅ Failure path` per code step)
- P6 architecture / dependency graph and a single locked build order **6.0 → 6.1 → 6.2 → 6.3 → 6.4 → 6.5**
- Locked design decisions with **no optional/either-or** language for P6 contracts (ownership 403, claim endpoint, SSE terminal buffering, proxy headers, Protocol backends, absolute min-places 409, cache-hit persistence)
- Sub-steps **6.0–6.4** with clear TASK bodies, plus **6.5** ship checklist / verification
- Recommended OpenSpec **batched** implementation clusters including `6.0`
- Full verification checklist and ship criteria table aligned to blueprint P6.5 plus v2 criteria (polyline LineStrings, single terminal frame, claim)
- Citation that Planner SoT is `docs/blueprint_final.md` v6.1
- Explicit abstraction map: `RateLimiterBackend`, `CacheBackend`, `RoutingProvider` (incl. `route_polyline`), LLM gateway — swap via settings/DI without router rewrites

#### Scenario: Agent can implement without inventing contracts
- **WHEN** an implementer opens `docs/steps/step6.md`
- **THEN** every P6 module has an ordered sub-step with explicit APIs, fallbacks, and a runnable ✅ validation command

#### Scenario: Blueprint remains SoT, prompt remains build contract
- **WHEN** product SSE / trips / cache rules need authority
- **THEN** `docs/blueprint_final.md` v6.1 is cited as Planner SoT and `step6.md` encodes those locks for Cursor apply sessions

#### Scenario: Implementation uses batched OpenSpec applies
- **WHEN** implementers start coding from the prompt
- **THEN** the prompt documents cluster batches (6.0, 6.1, 6.2, 6.3, 6.4–6.5) and MUST NOT require one propose→archive ceremony per micro-step

### Requirement: Trip persistence with Unit of Work and guest ownership
The system MUST implement `TripRepository` and `TripService.save_from_state(state, user_id, session_id) → Trip | None` such that Trip + TripPlace rows are written in **one transaction**. Partial TripPlace failure MUST roll back the entire save (no Trip without its places). Field mapping MUST follow the v2 locked mapping (including `TripPlace.polyline` from `leg_polyline`). Empty clarification/abort with no usable schedule MUST NOT create a Trip row (`None`).

Unauthenticated access to a trip MUST require the `wandr_session` cookie to **exactly match** `Trip.session_id`; mismatch or missing cookie MUST return **403** (same class of failure as an authenticated user accessing another user’s trip). Guests with matching session MAY access trips where `user_id IS NULL` prior to claim. Step **6.1** MUST deliver the service/repository/schemas/exceptions surface (`save_from_state`, `assert_can_access`, `claim_for_user`) unit-testable with a DB session and MUST NOT register trips HTTP routes.

The system MUST implement `TripService.claim_for_user(trip, user_id, session_id)`. `POST /api/v1/trips/{id}/claim` (`require_auth`) MUST be registered in step **6.3** (not 6.1): succeed only when `trip.user_id IS NULL` and session matches; otherwise **403** (session) or **409** (`TripAlreadyClaimedError`).

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
- **THEN** `TripAlreadyClaimedError` is raised (HTTP 409 once the 6.3 route exists)

#### Scenario: Step 6.1 has no trips HTTP yet
- **WHEN** step 6.1 validation runs after trips service/repo land
- **THEN** `TripService` exposes `save_from_state` and `claim_for_user` and trips router endpoints are still unregistered

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

### Requirement: Trips CRUD and GeoJSON
The system MUST expose:
- `GET /api/v1/trips` → `PaginatedResponse[TripOut]` with `require_auth`
- `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` with `optional_auth` + ownership
- `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (public)
- `DELETE /api/v1/trips/{id}` → 204 with `require_auth` + ownership
- `POST /api/v1/trips/{id}/claim` → `ApiResponse[TripOut]` with `require_auth` + session match + unclaimed

GeoJSON MUST be built from persisted trip data (no live OSRM on read) and MUST include LineString features when polylines exist. Accessing another user’s trip or guest session mismatch MUST return **403**. Anonymous DELETE is forbidden by design.

#### Scenario: GeoJSON is map-renderable
- **WHEN** `GET /api/v1/trips/{id}/geojson` is called for a saved trip with polylines/coords
- **THEN** the body is a valid GeoJSON FeatureCollection suitable for geojson.io and includes at least one LineString when polylines were persisted

#### Scenario: List requires auth
- **WHEN** an unauthenticated client calls `GET /api/v1/trips`
- **THEN** the API returns 401

### Requirement: Swappable cache and rate-limit backends with fallbacks
The system MUST select rate-limit and planner-cache backends via Protocols and settings:
- Empty `REDIS_URL` → in-memory implementations
- Non-empty `REDIS_URL` → Redis implementations behind the same Protocols

Planner cache MUST store a JSON-serializable `TravelState` subset sufficient for SSE display and `save_from_state` (schedule with polylines, itinerary, prefs). MVP cache key MUST be `sha256(destination_id + sha256(normalized_raw_input) + days_or_0 + round(base_lat,3) + round(base_lng,3))` with TTL from `PLANNER_CACHE_TTL_SECONDS`. A cache hit MUST skip the tool loop only and MUST still run `save_from_state`, producing a **new** `trip_id`. Cache unavailable/error MUST skip cache and run the agent fresh (never 500). Rate limiter backend errors MUST continue to fail open + log warning.

Routers and domain services MUST NOT import Redis client libraries directly; only backend modules may.

Changing `LLM_MODEL` MUST require zero application code changes (existing LLM gateway). Swapping routing implementations MUST continue to go through `RoutingProvider`.

#### Scenario: Same cacheable input hits cache and still persists
- **WHEN** two generate requests share the same cache key components within TTL
- **THEN** the second response skips tool-loop events, still yields `itinerary_done` with a **new** `trip_id`, and does not re-run the tool loop

#### Scenario: Redis down does not break planning
- **WHEN** Redis is configured but unavailable
- **THEN** rate limiting fails open and planner cache is skipped; generation still proceeds

#### Scenario: Planner rate limit returns 429
- **WHEN** a client exceeds 10 req/min (default) on `/api/v1/planner/generate`
- **THEN** the API returns 429 with `Retry-After` and `ErrorResponse`

### Requirement: Backend ship checklist and import guards
P6 completion MUST verify the blueprint P6.5 checklist items relevant to shipped code: envelopes, destinations/places happy paths, SSE generate with single terminal/`trip_id`, GeoJSON (LineString when available), claim flow, resilience flags, evaluation rows, pytest green, no litellm outside `core/llm/client.py`, no geo imports inside `travel_engine/`, no tool-impl imports in graph nodes, no redis imports in planner/trips routers, no `StreamingResponse` in `planner/service.py`, and `LLM_MODEL` swap without code changes.

`docs/context.md` MUST be updated only after validations pass: mark **6.0–6.5** ✅, list live planner/trips/claim endpoints, note reverse-proxy buffering off for `/planner/generate`, note frontend must use `fetch()` (not `EventSource`) for POST SSE, set Next step → P7.1.

#### Scenario: Ship gate refuses incomplete P6
- **WHEN** SSE generate, trips GeoJSON, or claim is missing or pytest fails
- **THEN** `docs/context.md` MUST NOT claim P6 complete

#### Scenario: Provider swap via env
- **WHEN** `LLM_MODEL` is changed in environment/settings
- **THEN** no application source changes are required for the new model to be used by the LLM gateway
