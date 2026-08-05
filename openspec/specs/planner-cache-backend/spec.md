## Purpose

P6.4 planner result cache — swappable `CacheBackend` (InMemory / Redis), MVP cache key, and cache-hit replay that still persists a new Trip via `save_from_state`.

## Requirements

### Requirement: CacheBackend Protocol with in-memory and Redis implementations
The system MUST provide a `CacheBackend` Protocol in `src/core/cache/` with:
- `async def get(self, key: str) -> str | None`
- `async def set(self, key: str, value: str, ttl_seconds: int) -> None`

The system MUST implement `InMemoryCacheBackend` and `RedisCacheBackend`. `get_cache_backend()` MUST return Redis when `get_settings().REDIS_URL` is non-empty, otherwise InMemory. Redis clients MUST use explicit connect and socket/read timeouts. Errors on `get` MUST be logged and treated as a miss (`None`). Errors on `set` MUST be logged and treated as a no-op. Backends MUST NOT raise to callers in a way that surfaces as HTTP 500 for planner generate.

Routers and domain modules under `src/planner/` and `src/trips/` MUST NOT import the `redis` package; only `src/core/` backend modules may.

#### Scenario: Empty REDIS_URL selects in-memory cache
- **WHEN** `REDIS_URL` is empty
- **THEN** `get_cache_backend()` returns an in-memory backend

#### Scenario: REDIS_URL selects Redis cache
- **WHEN** `REDIS_URL` is a non-empty URL
- **THEN** `get_cache_backend()` returns a Redis-backed `CacheBackend`

#### Scenario: Cache get error is a miss
- **WHEN** the cache backend raises during `get`
- **THEN** the caller receives `None` (miss) and a warning is logged

#### Scenario: Cache set error is ignored
- **WHEN** the cache backend raises during `set`
- **THEN** the operation is swallowed after logging and generation is unaffected

### Requirement: Planner MVP cache key and TravelState subset
Planner cache helpers MUST compute the locked MVP key:

`sha256(f"{destination_id}:{sha256(normalized_raw_input)}:{days_or_0}:{round(base_lat,3)}:{round(base_lng,3)}")`

where `normalized_raw_input` is `PlanRequest.raw_input` with strip + collapsed internal whitespace, and `days_or_0` is `PlanRequest.days` if set else `0`. TTL MUST come from `PLANNER_CACHE_TTL_SECONDS`.

Cached values MUST be a JSON-serializable subset of final `TravelState` sufficient for SSE display and `TripService.save_from_state`, including at least `schedule` (with `leg_polyline`/`day_polyline`), `itinerary`, preference fields (`interests`, `budget`, `include_offbeat`, `include_trekking`, `days`), `destination_id`, and completion flags (`plan_complete`, `abort_triggered`). Preference-semantic keys (`interests`/`budget` after parse) MUST NOT be used as the primary key in P6.

#### Scenario: Key includes rounded base coords and normalized raw_input
- **WHEN** two PlanRequests differ only by whitespace in `raw_input` or base coords within the same 0.001° rounding bucket
- **THEN** they resolve to the same cache key

#### Scenario: Different days produce different keys
- **WHEN** two otherwise identical requests differ in `days` (including None vs a set value)
- **THEN** they resolve to different cache keys

### Requirement: Cache hit skips tool loop but still persists a new trip
`maybe_get_cached_state` MUST return the deserialized state subset on hit, or `None` on miss/backend error. `_replay_cached(cached_state, on_event)` MUST emit SSE progress toward a terminal `itinerary_done` **without** emitting `tool_started` / `tool_done`, and MUST return a final-state dict shaped for `save_from_state`.

On a successful **fresh** generation (`plan_complete` and not `abort_triggered` with usable schedule), the system MUST best-effort `CacheBackend.set` the cacheable subset with the MVP key and TTL. Cache-hit requests MUST still run the router's existing `save_from_state` path and MUST produce a **new** `trip_id` (not reuse a prior trip id from the cache blob).

#### Scenario: Second identical generate uses cache and still saves
- **WHEN** two generate requests share the same MVP cache key within TTL after a successful fresh generation was cached
- **THEN** the second stream skips `tool_started`/`tool_done`, yields `itinerary_done` with a `trip_id`, and that `trip_id` differs from the first response's `trip_id`

#### Scenario: Redis unavailable still generates fresh
- **WHEN** Redis is configured but get/set raise
- **THEN** generate proceeds as a cache miss / without failing the request
