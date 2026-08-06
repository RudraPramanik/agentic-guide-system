## Why

P7.2 shipped TripService day surgery (`reorder_stops` / `remove_stop` / `add_stop` / `reoptimize_day`) with Fake coverage, but those ops are not reachable over HTTP. Step **7.3** (`docs/steps/step7.md`) is the next build-contract batch: expose the four blueprint edit endpoints with `require_auth` + ownership + a **user-keyed** rate-limit dependency so OSRM-costly edits cannot be hammered via UUID path-table hacks. Without this step, owners cannot mutate saved trips from the API surface.

## What Changes

- Add `RATE_LIMIT_TRIP_EDIT_REQUESTS` / `RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS` to Settings (defaults 20 / 60).
- Add a small `RateLimitedError` (`WandrError`, 429, `rate_limit_exceeded`) — middleware today returns `ErrorResponse` inline; the FastAPI dependency needs a raiseable type that reuses the global `WandrError` handler.
- Implement `rate_limit_trip_edit` dependency: key `{user_id}:trip_edit` via `get_rate_limiter().is_allowed`; fail-open on limiter exceptions; **do not** add UUID edit paths to `_route_limit_table` (dual IP middleware default is OK).
- Extend `src/trips/router.py` with the four edit routes → `TripService` only → `ApiResponse[TripOut]`.
- Thin HTTP tests proving OpenAPI registration, owner 200, guest 401, non-owner 403, and 21st rapid edit → 429 (mock limiter). Full edit suite remains 7.4.
- Update `docs/context.md` after validation (Next → 7.4).

**Non-goals:** Full `tests/trips/test_edit_replan.py` matrix (7.4); evaluation polish beyond existing thin `mark_trip_edited` (7.5); smoke/docs cadence (7.6); changing TripService edit semantics; PlannerService / `execute_tool` / LLM on edit path; new packages/migrations; adding edit paths to the middleware path-limit table.

**Naming note:** Blueprint Phase Blueprint labels HTTP as “7.2” and tests as “7.3”; `docs/steps/step7.md` v2.1 expands P7 to **7.0–7.6** with this work as **7.3**. Build from the step contract; product paths/bodies/auth follow the blueprint P7 table with intentional deltas locked in step7 (user-keyed rate limit; travel_engine + `RoutingProvider`, not TOOL_REGISTRY).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `p7-trip-edit-replan`: Fulfill the day-scoped edit **HTTP** surface — four routes registered, `ApiResponse[TripOut]`, auth/ownership/429 scenarios live (service semantics already landed in 7.2).
- `trips-http-crud-geojson`: Lift the “no P7 edit routes” constraint; extend the trips auth matrix with the four edit endpoints while keeping existing CRUD/GeoJSON/claim unchanged.
- `rate-limit-middleware`: Add settings + user-keyed `rate_limit_trip_edit` dependency contract (fail-open, 429 via WandrError); explicitly forbid UUID edit paths in `_route_limit_table`.

## Impact

- **Code:** `src/config.py`; `src/core/exceptions.py` (or adjacent); `rate_limit_trip_edit` dependency (trips or core/security); `src/trips/router.py`; thin `tests/trips/` HTTP coverage.
- **AGENT.md:** Router → Service only; `ApiResponse[T]`; env via `get_settings()`; no redis/litellm imports in router; no LLM/planner on edit.
- **Blueprint patterns:** Service Layer (thin router), Circuit Breaker / fail-open rate limit, Configuration Object.
- **Depends on:** P7.2 TripService public edit methods + schemas/exceptions; existing `get_rate_limiter()` / `RateLimiterBackend`.
- **Unlocks:** 7.4 full edit/replan pytest suite against live HTTP + service.
- **Live endpoints:** four new authenticated edit routes under `/api/v1/trips/...`.
- **No DB migration / no new packages.**
