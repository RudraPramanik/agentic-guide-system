## Why

P6.0–6.3 shipped geometry, trip persistence, SSE generate (always-miss cache stub), and trips HTTP — but rate limiting is still process-local in-memory only, and planner cache is not real yet. Step6's recommended OpenSpec batch is **`6.4–6.5`**: land swappable Redis backends + cache-hit-still-persists (**6.4**), then close P6 with the full test/smoke/import-guard ship gate and `docs/context.md` → P7.1 (**6.5**). Doing them together avoids a half-stamped phase and matches the canonical build contract in `docs/steps/step6.md` (SoT: `docs/blueprint_final.md` v6.1; MVP cache key from hardened v2).

## What Changes

### 6.4 — Redis backends + planner cache
- Add `redis>=5,<6` to `requirements.txt` (why-comment; pin exact version once verified).
- Implement `CacheBackend` Protocol + `InMemoryCacheBackend` + `RedisCacheBackend` under `src/core/cache/` with `get_cache_backend()` selecting on `REDIS_URL`.
- Extend rate-limit module: `RedisRateLimiter` + make `get_rate_limiter()` select InMemory vs Redis.
- Wire planner cache in `src/planner/cache.py`: locked MVP key, real get/set, `_replay_cached` (skip tool loop; still feeds `save_from_state`).
- Best-effort cache **set** after successful fresh generation; hit path still creates a **new** `trip_id`.

### 6.5 — Ship checklist + smoke + context
- Fill remaining P6 pytest gaps called out in step 6.5 (polyline regression, trips UoW/ownership/claim/geojson, planner SSE floor/single-terminal/cache-hit, core Redis fail-open) where not already covered.
- Add `scripts/test_p6_smoke.py` (search/readiness/places → generate SSE → geojson LineString → cache-hit second generate → claim 200/409 → import guards).
- Run full `pytest tests/ -v` + smoke; only then stamp `docs/context.md` Progress **6.0–6.5** ✅, Next → **P7.1**.
- Out of this change: Redis in docker-compose (F4); preference-semantic cache keys (post-MVP); P7 edit/replan routes.

## Capabilities

### New Capabilities

- `planner-cache-backend`: `CacheBackend` Protocol + in-memory/Redis implementations; MVP key; get/set/replay so cache hits skip the tool loop but still persist a new Trip.
- `p6-ship-verification`: P6.5 pytest coverage gaps, `scripts/test_p6_smoke.py`, import guards, and context P6-complete stamp only after green.

### Modified Capabilities

- `rate-limit-middleware`: Deliver Redis `RateLimiterBackend` selection via `get_rate_limiter()` when `REDIS_URL` is set.
- `planner-sse-generate`: Replace always-miss stub with real hit/set + replay; same `save_from_state` path.
- `p6-planner-api-persistence`: Deliver 6.4 backends + activate 6.5 ship checklist / context gate in this same change (no longer forward-locked).

## Impact

- **Code:** `src/core/cache/backends.py`; rate_limit Redis factory; `src/planner/cache.py` + router set hook; `requirements.txt` (+ redis); `scripts/test_p6_smoke.py`; focused tests under `tests/core/`, `tests/planner/`, `tests/trips/`, `tests/travel_engine/` as needed.
- **APIs:** No new routes. Cache hits may skip `tool_*` SSE events and still return a new `trip_id`.
- **Deps:** First `redis` package (`redis.asyncio`); only under `src/core/`.
- **AGENT.md:** Explicit Redis timeouts; fail-open; no redis in planner/trips routers; service stays free of `StreamingResponse`.
- **Blueprint note:** Root §6.4 preference-level key wording yields to step6 v2 raw-input MVP key (already locked in main specs).
- **Docs:** After green only — context Next → P7.1; deployment proxy note + frontend `fetch()` SSE note retained/confirmed.
- **Prerequisites (verified):** P6.0–6.3 ✅; generate + trips routes live; cache stubs; in-memory-only limiter factory; no `redis` package / no `src/core/cache/` / no `scripts/test_p6_smoke.py` yet.
