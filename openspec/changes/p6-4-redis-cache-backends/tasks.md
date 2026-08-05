## 1. Dependency + settings (6.4)

- [ ] 1.1 Add `redis>=5,<6` to `requirements.txt` with why-comment (P6.4 rate limit + planner cache); pin exact version after install verifies
- [ ] 1.2 Add Redis timeout settings via `get_settings()` (connect + socket/read defaults ~1s) — no hardcoded timeouts in backends
- [ ] 1.3 Confirm `.env.example` documents `REDIS_URL` (empty = in-memory) if not already clear

## 2. CacheBackend (6.4)

- [ ] 2.1 Create `src/core/cache/backends.py` with `CacheBackend` Protocol, `InMemoryCacheBackend` (TTL-aware), `RedisCacheBackend` (explicit timeouts), `get_cache_backend()`, and test reset helper
- [ ] 2.2 Ensure get/set never raise to callers — log + miss / no-op set
- [ ] 2.3 Add `src/core/cache/__init__.py` re-exports as needed

## 3. Redis rate limiter (6.4)

- [ ] 3.1 Implement `RedisRateLimiter(RateLimiterBackend)` with sliding-window semantics close to `InMemoryRateLimiter`
- [ ] 3.2 Update `get_rate_limiter()` to select InMemory vs Redis from `REDIS_URL` (lazy singleton + test reset)
- [ ] 3.3 Preserve middleware fail-open: Redis errors → allow + warning (never 500)

## 4. Planner cache wire-up (6.4)

- [ ] 4.1 Implement MVP key builder (normalized `raw_input`, `days_or_0`, rounded base lat/lng) in `src/planner/cache.py`
- [ ] 4.2 Implement `maybe_get_cached_state` via `get_cache_backend().get` + JSON deserialize; errors → `None`
- [ ] 4.3 Implement `_replay_cached` — emit non-tool SSE events + return `save_from_state`-ready dict (no `tool_started`/`tool_done`)
- [ ] 4.4 Implement `maybe_set_cached_state` (or equivalent) for successful fresh completes; lean TravelState subset only
- [ ] 4.5 Hook best-effort cache set from planner router after fresh success; do not import `redis` in router

## 5. Focused 6.4 validation

- [ ] 5.1 Run step 6.4 factory check: empty `REDIS_URL` → `isinstance(get_rate_limiter(), InMemoryRateLimiter)`
- [ ] 5.2 Import guard: zero `import redis` / `from redis` under `src/planner` and `src/trips`
- [ ] 5.3 Add focused tests: cache key normalization/rounding; in-memory hit/miss/TTL; Redis backend error → miss/no-op (mocked); limiter factory selection; cache hit → new `trip_id` without `tool_*` events
- [ ] 5.4 Run focused pytest for new/changed modules — green before proceeding to 6.5

## 6. P6.5 pytest gaps

- [ ] 6.1 Ensure `tests/travel_engine/` polyline regression (leg_polylines alignment, day_polyline, None-on-fallback) — add if missing
- [ ] 6.2 Ensure `tests/trips/` covers save_from_state UoW + polyline, ownership 403, claim 200/403/409, geojson LineString — fill gaps only
- [ ] 6.3 Ensure `tests/planner/` covers 409 floor, single terminal-event regression, disconnect cancel, cache-hit new trip_id — fill gaps only
- [ ] 6.4 Ensure `tests/core/` covers Redis limiter/cache selection + fail-open (mocked)

## 7. P6.5 smoke + full verification

- [ ] 7.1 Create `scripts/test_p6_smoke.py` with sections 1–6 from step6.5 (search/readiness/places → generate → geojson → cache-hit generate → claim → import guards); non-zero exit on failure
- [ ] 7.2 Run `python -m pytest tests/ -v` — all green
- [ ] 7.3 Run `python scripts/test_p6_smoke.py` — all green
- [ ] 7.4 Run step6 full verification import guards (litellm scope, travel_engine purity, redis not in planner/trips, no StreamingResponse in planner service)

## 8. Context (only after green)

- [ ] 8.1 Update `docs/context.md`: Progress **6.0–6.5** ✅, Next → **P7.1**; implemented modules for CacheBackend + Redis rate limiter; clear cache stub notes; confirm live endpoints + proxy/frontend notes; keep P7 edit ops as stubs
- [ ] 8.2 Do not add docker-compose Redis; do not claim P7 complete; do not stamp P6 complete if pytest or smoke failed
