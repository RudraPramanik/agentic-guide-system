## ADDED Requirements

### Requirement: Hardened P6 Cursor prompt exists as step6.md
The project SHALL provide `docs/steps/step6.md` as the sole P6 implementation prompt, modeled on `docs/steps/step5.md` / `docs/steps/step4.md`.

The prompt MUST include:
- Prerequisites (P5 complete — especially `PlannerService.generate` bridge + compiled graph — from `docs/context.md`)
- Prompt conventions and failure standards (`FAILURE BOUNDARY` + `✅ Failure path` per code step)
- P6 architecture / dependency graph and a single locked build order **6.1 → 6.5**
- Locked design decisions with **no optional/either-or** language for P6 contracts (ownership 403, SSE queue, Protocol backends, absolute min-places 409)
- Sub-steps **6.1–6.4** with clear TASK bodies, plus **6.5** ship checklist / verification
- Recommended OpenSpec **batched** implementation clusters
- Full verification checklist and ship criteria table aligned to blueprint P6.5
- Citation that Planner SoT is `docs/blueprint_final.md` v6.1
- Explicit abstraction map: `RateLimiterBackend`, `CacheBackend`, `RoutingProvider`, LLM gateway — swap via settings/DI without router rewrites

#### Scenario: Agent can implement without inventing contracts
- **WHEN** an implementer opens `docs/steps/step6.md`
- **THEN** every P6 module has an ordered sub-step with explicit APIs, fallbacks, and a runnable ✅ validation command

#### Scenario: Blueprint remains SoT, prompt remains build contract
- **WHEN** product SSE / trips / cache rules need authority
- **THEN** `docs/blueprint_final.md` v6.1 is cited as Planner SoT and `step6.md` encodes those locks for Cursor apply sessions

#### Scenario: Implementation uses batched OpenSpec applies
- **WHEN** implementers start coding from the prompt
- **THEN** the prompt documents cluster batches (6.1, 6.2, 6.3, 6.4–6.5) and MUST NOT require one propose→archive ceremony per micro-step

### Requirement: Trip persistence with Unit of Work and guest ownership
The system MUST implement `TripRepository` and `TripService.save_from_state(state, user_id, session_id) → Trip` such that Trip + TripPlace rows are written in **one transaction**. Partial TripPlace failure MUST roll back the entire save (no Trip without its places).

Unauthenticated access to a trip MUST require the `wandr_session` cookie to **exactly match** `Trip.session_id`; mismatch or missing cookie MUST return **403** (same class of failure as an authenticated user accessing another user’s trip).

#### Scenario: Save then reload includes all stops
- **WHEN** `save_from_state` is called with a complete itinerary state
- **THEN** a `trip_id` is returned and `get_with_places` returns every persisted stop

#### Scenario: Guest session mismatch is forbidden
- **WHEN** an unauthenticated client requests a trip whose `session_id` does not match `wandr_session`
- **THEN** the API returns HTTP 403 (not 404)

#### Scenario: Partial insert rolls back
- **WHEN** a TripPlace insert fails mid-save
- **THEN** no Trip row remains committed for that attempt

### Requirement: Planner generate SSE HTTP endpoint with pre-graph floor
The system MUST expose `POST /api/v1/planner/generate` accepting `PlanRequest(destination_id, raw_input, days?, base_lat?, base_lng?)` and returning `StreamingResponse` with `content-type: text/event-stream`.

SSE event names MUST include at least: `preferences_done`, `phase_changed`, `tool_started`, `tool_done`, `validation_done`, `itinerary_done`, `clarification_needed`, `error`.

The endpoint MUST use `optional_auth`. Omitted `base_lat`/`base_lng` MUST default to the destination center. If destination `place_count < PLANNER_ABSOLUTE_MIN_PLACES`, the endpoint MUST return HTTP **409** with code `destination_not_ready` and MUST NOT invoke the planner graph.

SSE design MUST run generation as a background task; tool/service `emit`/`on_event` hooks push into an `asyncio.Queue`; the response generator yields events while the graph runs; `request.is_disconnected()` MUST cancel the background task. The service `PLANNER_GENERATION_TIMEOUT_SECONDS` ceiling MUST still apply; timeout/disconnect MUST emit SSE `error` (or clean cancel) and close — never hang and never await-full-invoke-then-dump.

`PlannerService` MUST remain free of FastAPI `Request`/`StreamingResponse` types; the router is the SSE adapter over `generate(..., on_event=...)`.

#### Scenario: Stream emits while generation runs
- **WHEN** a valid plan request is posted for a ready destination
- **THEN** SSE events are yielded during generation (not only after completion) and a final `itinerary_done` or `error`/`clarification_needed` closes the logical stream

#### Scenario: Absolute min places rejects before graph
- **WHEN** destination `place_count` is below `PLANNER_ABSOLUTE_MIN_PLACES`
- **THEN** response is HTTP 409 with `destination_not_ready` and no tool loop runs

#### Scenario: Timeout closes stream cleanly
- **WHEN** generation exceeds `PLANNER_GENERATION_TIMEOUT_SECONDS`
- **THEN** an SSE `error` event is emitted and the stream closes without hanging

#### Scenario: Disconnect cancels server work
- **WHEN** the client disconnects mid-stream
- **THEN** the background generation task is cancelled (no continued unbounded LLM spend for that request)

### Requirement: Trips CRUD and GeoJSON
The system MUST expose:
- `GET /api/v1/trips` → `PaginatedResponse[TripOut]` with `require_auth`
- `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` with `optional_auth` + ownership
- `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (public)
- `DELETE /api/v1/trips/{id}` → 204 with `require_auth` + ownership

GeoJSON MUST be built from persisted trip data (no live OSRM on read). Accessing another user’s trip or guest session mismatch MUST return **403**.

#### Scenario: GeoJSON is map-renderable
- **WHEN** `GET /api/v1/trips/{id}/geojson` is called for a saved trip with polylines/coords
- **THEN** the body is a valid GeoJSON FeatureCollection suitable for geojson.io

#### Scenario: List requires auth
- **WHEN** an unauthenticated client calls `GET /api/v1/trips`
- **THEN** the API returns 401

### Requirement: Swappable cache and rate-limit backends with fallbacks
The system MUST select rate-limit and planner-cache backends via Protocols and settings:
- Empty `REDIS_URL` → in-memory implementations
- Non-empty `REDIS_URL` → Redis implementations behind the same Protocols

Planner cache key MUST be `sha256(destination_id + sorted_interests + days + budget + round(base_lat,3) + round(base_lng,3))` with ~1 hour TTL from settings. Caching is best-effort at parsed-preference level. Cache unavailable/error MUST skip cache and run the agent fresh (never 500). Rate limiter backend errors MUST continue to fail open + log warning.

Routers and domain services MUST NOT import Redis client libraries directly; only backend modules may.

Changing `LLM_MODEL` MUST require zero application code changes (existing LLM gateway). Swapping routing implementations MUST continue to go through `RoutingProvider`.

#### Scenario: Same cacheable input hits cache
- **WHEN** two generate requests share the same cache key components within TTL
- **THEN** the second response is served from cache without re-running the tool loop (SSE still completes with itinerary payload)

#### Scenario: Redis down does not break planning
- **WHEN** Redis is configured but unavailable
- **THEN** rate limiting fails open and planner cache is skipped; generation still proceeds

#### Scenario: Planner rate limit returns 429
- **WHEN** a client exceeds 10 req/min (default) on `/api/v1/planner/generate`
- **THEN** the API returns 429 with `Retry-After` and `ErrorResponse`

### Requirement: Backend ship checklist and import guards
P6 completion MUST verify the blueprint P6.5 checklist items relevant to shipped code: envelopes, destinations/places happy paths, SSE generate, GeoJSON, resilience flags, evaluation rows, pytest green, no litellm outside `core/llm/client.py`, no geo imports inside `travel_engine/`, no tool-impl imports in graph nodes, and `LLM_MODEL` swap without code changes.

`docs/context.md` MUST be updated only after validations pass: mark 6.1–6.5 ✅, list live planner/trips endpoints, set Next step → P7.1.

#### Scenario: Ship gate refuses incomplete P6
- **WHEN** SSE generate or trips GeoJSON is missing or pytest fails
- **THEN** `docs/context.md` MUST NOT claim P6 complete

#### Scenario: Provider swap via env
- **WHEN** `LLM_MODEL` is changed in environment/settings
- **THEN** no application source changes are required for the new model to be used by the LLM gateway
