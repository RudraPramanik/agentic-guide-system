## Context

P1 is complete (DB, auth, middleware, pytest). `src/geo/*` remains step-0.1 stubs. P2 canonical order starts at step 2.1 (`docs/steps/step2.md`): geo schemas + Nominatim gateway before Overpass (2.2), place repo (2.3), and destinations. AGENT.md requires all Nominatim I/O inside `src/geo/`. Blueprint resilience: Nominatim → tenacity 3× → return `None`.

## Goals / Non-Goals

**Goals:**
- Real `GeocodedPlace`, `RawPOI`, `RouteResult` DTOs in `src/geo/schemas.py`
- Working `geocode()` with timeouts, retry, User-Agent, process-local dict cache + 1 req/sec throttle
- Config: `NOMINATIM_BASE_URL`, `OVERPASS_API_URL` (+ `.env.example`)
- CLI `scripts/test_geocoder.py` and failure/cache validation paths from step 2.1
- Document per-process cache/throttle limitation in `docs/context.md` (P6 Redis follow-up)

**Non-Goals:**
- Overpass client (2.2), OSRM (2.5), place/destination repos or routers, seed script
- Multi-worker / Redis-backed cache or global Nominatim budget
- New package installs
- Full P2 pytest suite (2.9) — step 2.1 uses script + inline validation

## Decisions

### D1 — Manual dict cache, not `@lru_cache` on async
- **Why:** `@functools.lru_cache` on `async def` caches the coroutine object; second await raises `RuntimeError`. Step 2.1 v2 locks a `dict` of resolved `GeocodedPlace | None` under `asyncio.Lock`.
- **Alt:** `async-lru` / `cachetools` — rejected for P2; step contract is hand-rolled; no new deps.

### D2 — Cache confirmed misses (`None`)
- Avoid re-hitting Nominatim for known-bad queries within process lifetime.
- Misses are not persisted across restarts (acceptable for P2).

### D3 — Gateway isolation
- `_fetch_nominatim` owns URL, params, headers, timeouts; callers only use `geocode`.
- No SQLAlchemy/FastAPI in `geo/`.
- Retry only `TimeoutException` / `ConnectError`; 4xx → log warning, return `None` (no retry).

### D4 — Config now includes Overpass URL
- Step 2.1 adds `OVERPASS_API_URL` even though Overpass logic is 2.2 — matches step prompt so env is ready before scraper lands.
- `NOMINATIM_USER_AGENT` already exists; do not reinvent.

### D5 — Schemas include RawPOI and RouteResult early
- Defined in 2.1 so 2.2/2.5 do not redefine DTOs; no Overpass/OSRM logic in this change.

### D6 — Throttle only on outbound path
- Cache hits skip `_throttle()` and network; only cache-miss → throttle → fetch.
- Per-process only; multi-worker fragmentation is documented, not “fixed” in P2.

## Risks / Trade-offs

- [Per-process cache/throttle under multi-worker] → Document in context.md; P6 Redis shared cache/throttle
- [Public Nominatim rate/policy abuse] → User-Agent + 1 req/sec + cache misses; later destination search gets tighter path rate limit (2.6c′)
- [Live validation needs network] → Failure-path tests use mocks; live Darjeeling check is optional when offline
- [Caching None forever in-process] → Accept for P2; process restart clears; do not persist

## Migration Plan

1. Update `src/config.py` + `.env.example`
2. Implement `src/geo/schemas.py` and `src/geo/geocoder.py`
3. Add `scripts/test_geocoder.py`
4. Run step 2.1 validation (live + cache + failure mocks)
5. Update `docs/context.md` (2.1 ✅, Next → 2.2, implemented modules, stubs, P6 cache TODO)
6. Rollback: revert those files; no DB/migration impact

## Open Questions

- None blocking for 2.1.
