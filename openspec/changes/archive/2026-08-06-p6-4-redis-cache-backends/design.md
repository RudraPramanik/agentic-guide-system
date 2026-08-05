## Context

P6.0–6.3 are green: polyline threading, `TripService.save_from_state`, SSE `/planner/generate` (terminal buffer + save + proxy headers), trips CRUD/GeoJSON/claim. Cache helpers are stubs (`maybe_get_cached_state` → always `None`; `_replay_cached` → `NotImplementedError`). `get_rate_limiter()` always returns in-memory despite Protocol/spec readiness for Redis. No `scripts/test_p6_smoke.py` yet.

Step contract: `docs/steps/step6.md` §**6.4–6.5** (recommended OpenSpec batch). SoT: `docs/blueprint_final.md` v6.1. AGENT.md: explicit timeouts; no redis outside `src/core/`; no new packages without why-comment; context stamp only after validation.

**Prerequisite gate (verified):** context Next → P6.4; generate + trips live; `REDIS_URL=""` + `PLANNER_CACHE_TTL_SECONDS=3600`; no redis package / no `src/core/cache/`.

**Blueprint vs step6 cache key:** root blueprint §6.4 preference-level keys vs step6 v2 / main spec **raw-input MVP key** — this design follows the v2 lock.

## Goals / Non-Goals

**Goals:**

- **6.4:** `CacheBackend` + Redis/InMemory; `RedisRateLimiter` + factory selection; real planner cache (MVP key, get/set, `_replay_cached`, persist-on-hit).
- **6.5:** Close remaining P6 pytest gaps; `scripts/test_p6_smoke.py`; full pytest + smoke green; import guards; `docs/context.md` → Progress 6.0–6.5 ✅, Next **P7.1** (only after green).
- Fail-open everywhere Redis can fail.

**Non-Goals:**

- Redis in docker-compose (forward lock F4).
- Preference-semantic cache keys (post-MVP).
- Changing SSE terminal buffering, floor check, or trips HTTP contracts.
- P7 edit/replan routes or claiming P7 complete.
- Shared Redis connection pool beyond simple module singletons.

## Decisions

### D1 — Package: `redis` asyncio client

**Choice:** Add `redis>=5,<6` to `requirements.txt` with why-comment; pin exact version once verified. Use `redis.asyncio` for limiter and cache backends.

**Alternatives:** `aioredis` (merged into redis-py 5+) — rejected. Upstash REST-only — rejected.

### D2 — Module layout

| Piece | Location |
|-------|----------|
| `CacheBackend`, InMemory, Redis, `get_cache_backend` | `src/core/cache/backends.py` |
| `RedisRateLimiter`, factory update | `src/core/middleware/rate_limit.py` |
| Key / get / set / replay | `src/planner/cache.py` |
| P6 smoke | `scripts/test_p6_smoke.py` |

Routers/trips MUST NOT `import redis`.

### D3 — Redis timeouts (LOCKED resilience)

**Choice:** Explicit connect + socket/read timeouts from settings (add `REDIS_*_TIMEOUT` knobs if missing; defaults ~1s). No tenacity on cache/limiter Redis — fail fast to miss / fail-open. Never surface as HTTP 500.

### D4 — Factory / singleton selection

**Choice:** Lazy process singletons from `REDIS_URL`; empty → InMemory; non-empty → Redis. `_reset_*_for_tests()` helpers for pytest.

### D5 — MVP cache key (LOCKED v2)

```
normalized = strip + collapse whitespace on raw_input
days_or_0 = body.days if set else 0
key = sha256(f"{destination_id}:{sha256(normalized)}:{days_or_0}:{round(base_lat,3)}:{round(base_lng,3)}").hexdigest()
```

Optional prefix `wandr:planner:v1:` for namespace / schema bumps.

### D6 — Cached value shape (LOCKED)

JSON subset: `destination_id`, `schedule` (+ polylines), `itinerary`, prefs (`interests`/`budget`/`include_*`/`days`), `plan_complete=True`, `abort_triggered=False`. Lean — skip bulky working sets. `_replay_cached` emits non-`tool_*` events + returns save-ready dict.

### D7 — Cache SET after fresh success

**Choice:** Best-effort set from router/helper after fresh complete+usable schedule; skip set on cache-hit replay. Errors → log + ignore.

### D8 — Redis sliding-window rate limit

**Choice:** Prefer ZSET sliding window mirroring `InMemoryRateLimiter`; middleware fail-open unchanged.

### D9 — No compose Redis (LOCKED F4)

**Choice:** Empty `REDIS_URL` → in-memory; docker-compose stays Redis-free for MVP.

### D10 — Batch scope: 6.4 + 6.5 together (UPDATED)

**Choice:** Single OpenSpec change implements **6.4 then 6.5** in one apply session (matches step6 recommended batch). Apply order: backends → planner cache → focused 6.4 tests → fill 6.5 test/smoke gaps → full suite + smoke → context P6-complete. Do **not** stamp context mid-batch as “Next P6.5”; stamp once at end → P7.1.

**Alternatives:** Split propose cycles — rejected per user request and step6 cadence.

### D11 — Ship gate failure boundary (6.5)

**Choice:** Any pytest or smoke failure blocks updating `docs/context.md` to claim P6 complete. Prefer filling gaps over inventing duplicate tests when prior steps already cover a ship criterion.

### D12 — Smoke script shape

**Choice:** Offline-friendly where possible (in-memory cache, FakeRoutingProvider / seeded DB); live OSRM optional. Sections mirror step6.5: P2/P3 sanity → generate SSE → geojson → second generate cache path → claim → import guards.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Blueprint preference key vs v2 raw-input key | D5; follow step6/main spec |
| Cache hit drops tool_trace nuance | Documented MVP; store prefs in subset |
| Stale cache after shape change | `v1` key prefix + TTL |
| Redis hangs generate | Short timeouts |
| In-memory cache unbounded growth | TTL eviction on get/set |
| Large 6.4+6.5 apply session | Ordered tasks; 6.4 proof before smoke |
| Smoke needs seeded destination / auth | Reuse P2/P5 patterns; document env in script docstring |
| Premature context stamp | D11 — green gate only |

## Migration Plan

1. Implement 6.4 (dep → backends → cache wire-up → focused tests).
2. Implement 6.5 (gap tests → smoke script → full pytest + smoke).
3. Update `docs/context.md` only after green (6.0–6.5 ✅, Next P7.1).
4. Rollback: revert code + uninstall redis; empty REDIS_URL safe.

## Open Questions

None blocking. Optional later: blueprint §6.4 footnote for MVP key; in-memory max-keys; TTL refresh on hit.
