## MODIFIED Requirements

### Requirement: Swappable cache and rate-limit backends with fallbacks
The system MUST select rate-limit and planner-cache backends via Protocols and settings:
- Empty `REDIS_URL` → in-memory implementations
- Non-empty `REDIS_URL` → Redis implementations behind the same Protocols

Planner cache MUST store a JSON-serializable `TravelState` subset sufficient for SSE display and `save_from_state` (schedule with polylines, itinerary, prefs). MVP cache key MUST be `sha256(destination_id + sha256(normalized_raw_input) + days_or_0 + round(base_lat,3) + round(base_lng,3))` with TTL from `PLANNER_CACHE_TTL_SECONDS`. A cache hit MUST skip the tool loop only and MUST still run `save_from_state`, producing a **new** `trip_id`. Cache unavailable/error MUST skip cache and run the agent fresh (never 500). Rate limiter backend errors MUST continue to fail open + log warning.

Routers and domain services MUST NOT import Redis client libraries directly; only backend modules may.

Steps **6.4–6.5** in this change deliver these backends, the real cache hit/set path, the P6 ship checklist / smoke / import guards, and the context P6-complete stamp (Next → P7.1) only after validations pass.

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

#### Scenario: Empty REDIS_URL stays in-memory without docker Redis
- **WHEN** `REDIS_URL` is empty in local/MVP compose
- **THEN** both rate limit and planner cache use in-memory backends and require no Redis service

### Requirement: Backend ship checklist and import guards
P6 completion MUST verify the blueprint P6.5 checklist items relevant to shipped code: envelopes, destinations/places happy paths, SSE generate with single terminal/`trip_id`, GeoJSON (LineString when available), claim flow, resilience flags, evaluation rows, pytest green, no litellm outside `core/llm/client.py`, no geo imports inside `travel_engine/`, no tool-impl imports in graph nodes, no redis imports in planner/trips routers, no `StreamingResponse` in `planner/service.py`, and `LLM_MODEL` swap without code changes.

`docs/context.md` MUST be updated only after validations pass: mark **6.0–6.5** ✅, list live planner/trips/claim endpoints, note reverse-proxy buffering off for `/planner/generate`, note frontend must use `fetch()` (not `EventSource`) for POST SSE, set Next step → P7.1.

#### Scenario: Ship gate refuses incomplete P6
- **WHEN** SSE generate, trips GeoJSON, or claim is missing or pytest fails
- **THEN** `docs/context.md` MUST NOT claim P6 complete

#### Scenario: Provider swap via env
- **WHEN** `LLM_MODEL` is changed in environment/settings
- **THEN** no application source changes are required for the new model to be used by the LLM gateway

#### Scenario: Full suite and smoke pass before context stamp
- **WHEN** `python -m pytest tests/ -v` and `python scripts/test_p6_smoke.py` both succeed
- **THEN** `docs/context.md` may mark P6 complete and set Next → P7.1
