# Wandr — P2 Cursor Prompts: Geo Foundation (v2 — hardened)
> Blueprint: [`docs/blueprint_final.md`](../blueprint_final.md) — Phase P2 (4 days · 8 blueprint steps)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **v2 changelog:** fixes an async-cache correctness bug, a destination-upsert race condition,
> locks down two previously-ambiguous decisions, adds an endpoint-specific rate limit, adds the
> missing partial-failure test, and removes a broken validation script. See "v2 Fix Log" below.
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance to the next prompt until
> the current ✅ validation passes.

## v2 Fix Log (read this before implementing)

| # | Issue in v1 | Fix in v2 |
|---|---|---|
| 1 | `functools.lru_cache` on an `async def geocode()` — caches an already-awaited coroutine object, crashes on the 2nd (cache-hit) call | Hand-rolled `dict` cache guarded by `asyncio.Lock`, storing the *resolved value*, not the coroutine. See step 2.1. |
| 2 | `Destination.upsert_from_geocoded` was check-then-insert — two concurrent misses on the same new place raise `IntegrityError` → unhandled 500 | Rewritten as a single `INSERT ... ON CONFLICT (osm_place_id) DO UPDATE ... RETURNING` statement, same pattern as `Place.upsert_from_poi`. See step 2.6b. |
| 3 | Radius search left as "geography cast OR geometry" — an either/or that silently changes units (degrees vs meters) | Locked: always cast to `geography` explicitly. See step 2.3. |
| 4 | No endpoint-specific throttle on `/destinations/search` — every cache-miss is a live Nominatim call, only covered by P1's generic 60/min/IP limiter | New step 2.6c′ extends P1's rate limiter with a path-specific `20 req/min` rule for this route. |
| 5 | `PlaceService.list_by_destination` had destination-existence check marked "(optional)" | Locked: mandatory — raises `DestinationNotFoundError` (404), consistent with every other endpoint. See step 2.7a. |
| 6 | Geocoder in-process cache/throttle has no documented multi-worker limitation | Documented explicitly in step 2.1 as a known single-process constraint with a stated upgrade path (Redis-backed, deferred to P6 alongside the rate limiter's Redis backend). |
| 7 | No test asserting the seed script survives a single POI failure | Added explicit mocked test in step 2.9. |
| 8 | `upsert_from_poi` did an extra SELECT after the upsert | Now uses `.returning(Place)` — one round trip instead of two. See step 2.3. |
| 9 | Step 2.3's validation snippet contained a nonsensical `5.divmod(1)[0] or 5` expression that doesn't run | Replaced with a real, runnable validation script. |
| 10 | 2.4 depended on 2.6b but was numbered *before* it, patched with an "amendment" note | Removed the patch note — the canonical step order below is now the only order stated anywhere in this doc. |

---

## Prerequisites (P1 must be complete)

Before step 2.1, confirm P1 from `docs/context.md`:

- All P1 steps ✅ — models, `BaseRepository`, auth, middleware, pytest harness, `scripts/test_p1_smoke.py`
- Docker Postgres on host port **5433** (`DATABASE_URL=postgresql+asyncpg://wandr:wandr@localhost:5433/wandr`)
- `httpx==0.28.1` and `tenacity==9.1.4` already in `requirements.txt` from P0/P1 — **do not reinstall**
- `shapely==2.1.2` already in `requirements.txt` from step 1.12
- `.env` has a **real** `NOMINATIM_USER_AGENT` with contact email (Nominatim blocks generic agents)
- `python -m pytest tests/ -v` passes (37+ tests)
- `python scripts/test_p1_smoke.py` → `ALL P1 SMOKE TESTS PASSED`
- P1's `RateLimitMiddleware` and `_resolve_limits()` exist (step 1.10) — P2 step 2.6c′ extends `_resolve_limits`, it does not replace it.

## Prompt conventions (every step)

Each prompt block starts with `Read AGENT.md before proceeding.` Also:

- **Extend, don't replace** P1 code unless the step explicitly says replace.
- **Geo gateway rule:** Nominatim, Overpass, and OSRM HTTP calls happen **only** in `src/geo/`. Services and scripts call `geo/` functions — never construct OverpassQL or hit Nominatim URLs outside `src/geo/`.
- **Layering:** Router → Service → Repository. Routers never import `geo/` or SQLAlchemy directly.
- **Concurrency-safety rule (new in v2):** any repository write keyed by a unique external ID (`osm_id`, `osm_place_id`) MUST be a single atomic `INSERT ... ON CONFLICT ... DO UPDATE` statement — never a separate "look up, then insert" sequence. Two concurrent requests hitting the same not-yet-cached external ID is a normal case, not an edge case.
- **Failure boundaries:** external HTTP in `geo/` → retry per Resilience Contracts → named fallback (`None`, `[]`, haversine); never raw 500 from gateway modules. HTTP APIs → typed `WandrError` subclasses.
- **Time:** use `datetime.now(timezone.utc)`, never `datetime.utcnow()`.
- **httpx:** always explicit `httpx.Timeout(connect=..., read=..., write=..., pool=...)` — never bare `timeout=10.0`.
- **Commits:** repositories flush only; services/scripts commit. Match `AuthService` pattern.
- **Windows:** use `Select-String` instead of `grep` where noted in validation.
- **Failure standards:** every prompt has `─── FAILURE BOUNDARY ───` and a `✅ Failure path:` line.

---

## P2 architecture (read before implementing)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         P2 dependency graph (canonical order)        │
└──────────────────────────────────────────────────────────────────────┘

  2.1 geocoder ──┬─ 2.6a schemas/exceptions ─┬─ 2.6b repo/service (atomic upsert) ─┬─ 2.6c router
  2.2 overpass ──┤                            │                                     ├─ 2.6c′ rate limit
  2.3 place repo ┴──────────────────────────► 2.4 seed script ◄─────────────────────┘
                                                     │
                                                     ▼
                                              2.7a places service ─► 2.7b places router
                                                     │
                                                     ▼
                                              2.8 readiness
  2.5 osrm ── parallel track (standalone gateway; used by P4/P5 later)

  Layer rules:
    scripts/seed_destination.py  →  geo/ + repositories  →  commit
    GET /destinations/search       →  DestinationService   →  repo (atomic upsert) + geo.geocode
    GET /places                    →  PlaceService         →  PlaceRepository (mandatory dest check)
    geo/*                          →  httpx + tenacity     →  never touches DB
```

**Canonical build order (this is the only order stated in this document):**
```
2.1 → 2.2 → 2.3 → 2.6a → 2.6b → 2.4 → 2.5 → 2.6c → 2.6c′ → 2.7a → 2.7b → 2.8 → 2.9 → 2.10
```
Rationale: `2.4` (seed script) needs `DestinationRepository.upsert_from_geocoded` from `2.6b`, so `2.6a`/`2.6b` are built first. `2.5` (OSRM) has no dependents in P2 and can technically run anywhere after `2.3`, but is kept in sequence for a single linear path.

**Seed destination (default):** Darjeeling — used in all validation commands below.

---

## P2 design decisions (locked for implementation — no "optional" or "either/or" language remains)

### Category mapping (Overpass → `Place.category`)

Priority-ordered tag inspection in `src/geo/overpass.py`:

| OSM key | OSM value | `category` |
|---------|-----------|------------|
| `tourism` | `museum` | `museum` |
| `tourism` | `viewpoint` | `viewpoint` |
| `tourism` | `monastery` | `monastery` |
| `tourism` | `attraction` | `attraction` |
| `leisure` | `park` | `park` |
| `highway` | `trailhead` | `trailhead` |
| *(fallback)* | | `attraction` |

`osm_id` format: `"{element_type}/{id}"` (e.g. `node/12345`, `way/67890`).

### Readiness formula (`destinations/readiness.py` — pure function)

```python
PLACE_TARGET = 100  # place_count at which place component saturates

place_score = min(place_count / PLACE_TARGET, 1.0)
enriched_pct = enriched_count / place_count if place_count > 0 else 0.0
indexed_pct = (indexed_count / place_count) if (place_count > 0 and search_available) else 0.0

score = round(0.4 * place_score + 0.35 * enriched_pct + 0.25 * indexed_pct, 3)
tier = "ready" if score >= 0.7 else "limited" if score >= 0.3 else "sparse"
```

**P2 note:** Seeded Darjeeling (~144 places, 0 enriched, `search_available=False`) yields **score ≈ 0.4, tier = `limited`**. Tier `ready` requires P3 enrichment/indexing.

### Destination counters

`Destination.place_count`, `enriched_count`, `indexed_count` are **denormalized**. The seed script sets `place_count` after upserts. **Locked rule (v2):** `upsert_from_geocoded`'s `ON CONFLICT DO UPDATE` clause updates only geocode-derived fields (`name`, `country`, `display_name`, `lat`, `lng`, `updated_at`) — it must NEVER touch `place_count`/`enriched_count`/`indexed_count`. Those are owned exclusively by the seed/enrich/index scripts.

### Radius search unit — LOCKED (v2)

`find_within_radius` casts both sides to `geography` explicitly:

```python
from sqlalchemy import cast
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID

ST_DWithin(
    cast(Place.location, Geography),
    cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), Geography),
    radius_km * 1000,
)
```

Plain `geometry` SRID 4326 measures in **degrees**, not meters — using it directly would make every radius query silently wrong (e.g. `radius_km=30` would actually search ~3300km). This is not an implementer's choice; it is fixed by this decision.

### `/destinations/search` rate limit — LOCKED (v2)

Every cache-miss on this endpoint makes a live outbound call to Nominatim, which is a shared public resource with its own usage policy. The endpoint gets its **own** rate limit — tighter than P1's generic 60/min/IP default — enforced by extending P1's `RateLimitMiddleware` with a path-specific rule (`20 req/min/IP`). See step 2.6c′.

### Destination-existence check on `/places` — LOCKED (v2)

`PlaceService.list_by_destination` **always** verifies the destination exists and raises `DestinationNotFoundError` (404) if not — this was previously marked optional; it is now mandatory, matching the 404 behavior of `/destinations/{id}/readiness` and `/places/{id}`. A request against a garbage `destination_id` must return 404, never a silent `total=0`.

### Geocoder cache/throttle — known limitation (v2, documented not deferred silently)

The in-process `dict` cache and `asyncio.Lock`-based 1 req/sec throttle in `geo/geocoder.py` are **per-process**. Running multiple uvicorn workers means:
- the Nominatim 1 req/sec policy is only honored *per worker*, not globally, and
- the cache is fragmented (a cache hit on worker A is a cache miss on worker B).

This is acceptable for P2 (single-process dev / low-traffic MVP) but is a **known limitation**, not a silent gap. Upgrade path: when P6 wires `REDIS_URL` for the rate limiter's Redis backend, extend the same connection to back a shared geocode cache and a Redis-based token-bucket throttle. Track this as a named TODO in `docs/context.md`, not left implicit.

### Config additions (step 2.1)

Add to `src/config.py` and `.env.example`:

```python
NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
```

`NOMINATIM_USER_AGENT` and `OSRM_BASE_URL` already exist.

---

## Step 2.1 — geo/schemas.py + geo/geocoder.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement geo Pydantic schemas and the Nominatim geocoding gateway.
This is step 2.1. No new package installs — httpx and tenacity are already in requirements.txt.

─── UPDATE src/config.py + .env.example ───
Add:
  NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
  OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

─── IMPLEMENT src/geo/schemas.py ───

  from pydantic import BaseModel, Field

  class GeocodedPlace(BaseModel):
      """Result of a successful Nominatim geocode."""
      name: str
      lat: float
      lng: float
      osm_place_id: str          # Nominatim osm_type/osm_id composite, e.g. "relation/123"
      country: str               # country_code uppercased, or country name if code missing
      display_name: str

  class RawPOI(BaseModel):
      """Parsed Overpass element — used by overpass.py (step 2.2)."""
      osm_id: str                # "{type}/{id}"
      name: str
      lat: float
      lng: float
      category: str
      raw_tags: dict = Field(default_factory=dict)

  class RouteResult(BaseModel):
      """OSRM route result — used by osrm.py (step 2.5)."""
      distance_km: float
      duration_min: float
      encoded_polyline: str | None = None
      fallback_used: bool = False

─── IMPLEMENT src/geo/geocoder.py ───

  🏗️ Gateway Pattern — all geocoding through this module.

  ⚠️ CORRECTNESS-CRITICAL (v2): do NOT put @functools.lru_cache on an async function.
  lru_cache wraps a sync callable; decorating `async def geocode(...)` caches the
  *coroutine object* returned by calling it, not its resolved value. The first call
  awaits and consumes that coroutine; every subsequent "cache hit" hands back an
  already-awaited coroutine, which raises RuntimeError on await. Use the manual
  dict-based cache below instead.

  Module-level:
    - _HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
    - _rate_lock = asyncio.Lock()          # serializes outbound calls for the 1 req/sec throttle
    - _last_request_at: float = 0.0
    - _cache: dict[str, GeocodedPlace | None] = {}   # normalized query -> resolved result
    - _cache_lock = asyncio.Lock()                    # guards _cache reads/writes
    - _cache_hits: int = 0                            # exposed for test assertions only

  def _normalize(query: str) -> str:
      """Strip, collapse internal whitespace, lowercase — used as the cache key."""
      return " ".join(query.strip().lower().split())

  async def _throttle() -> None:
      """
      Enforce Nominatim's 1 req/sec policy between outbound calls, within this process.
      async with _rate_lock: compute elapsed since _last_request_at, asyncio.sleep the
      remainder if < 1.0s, then update _last_request_at = time.monotonic().
      """

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8),
         retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
  async def _fetch_nominatim(query: str) -> list[dict] | None:
      """
      GET {NOMINATIM_BASE_URL}/search
      Params: q, format=json, limit=1, addressdetails=1
      Headers: User-Agent from settings.NOMINATIM_USER_AGENT
      On 4xx: log warning, return None (no retry)
      On success: parse JSON list
      """

  def _parse_result(raw: dict) -> GeocodedPlace:
      """
      lat/lng from "lat"/"lon" strings -> float
      osm_place_id = f"{raw['osm_type']}/{raw['osm_id']}"
      country from address.country_code (upper) or address.country or "Unknown"
      name from raw["name"] or first segment of display_name
      """

  async def geocode(query: str) -> GeocodedPlace | None:
      """
      Public entry point. Manual cache — NOT lru_cache.

      1. normalized = _normalize(query)
      2. async with _cache_lock:
             if normalized in _cache:
                 _cache_hits += 1
                 return _cache[normalized]
      3. await _throttle()
      4. raw_results = await _fetch_nominatim(normalized)
      5. result = _parse_result(raw_results[0]) if raw_results else None
      6. async with _cache_lock:
             _cache[normalized] = result   # cache None too — a confirmed miss shouldn't re-hit Nominatim
      7. return result
      """

  def cache_stats() -> dict:
      """Test/debug helper: {"size": len(_cache), "hits": _cache_hits}."""

  def _clear_cache_for_tests() -> None:
      """Test-only reset — clears _cache and _cache_hits. Never called from app code."""

─── CREATE scripts/test_geocoder.py ───

  """CLI: python scripts/test_geocoder.py "Darjeeling" """
  import asyncio, sys
  from src.geo.geocoder import geocode

  async def main():
      query = sys.argv[1] if len(sys.argv) > 1 else "Darjeeling"
      result = await geocode(query)
      if result:
          print(f"GeocodedPlace(name={result.name!r}, lat={result.lat:.3f}, lng={result.lng:.3f})")
      else:
          print("Geocode failed — returned None")

  if __name__ == "__main__":
      asyncio.run(main())

─── RULES ───
- No SQLAlchemy, no FastAPI imports in geo/.
- geocode() returns None on failure — never raises httpx exceptions to callers.
- Cache stores the RESOLVED value (GeocodedPlace | None), never a coroutine or Task.
- A confirmed miss (None) is cached too, to avoid hammering Nominatim with a query that's
  known to fail — but only within this process's lifetime (no persistence across restarts).
- Retry only on TimeoutException and ConnectError — never on 404/400.
- Known limitation (see P2 design decisions): cache and throttle are per-process. Do not
  attempt to make this multi-worker-safe in P2 — that's an explicit P6/Redis follow-up.

─── FAILURE BOUNDARY ───
Blueprint row: Nominatim → tenacity 3x → return None.
Must NOT: raise httpx exceptions, return 500, call Nominatim without User-Agent, or crash
on a cache hit (the v1 lru_cache bug this step exists to prevent).

─── VALIDATION ───
Run:
  python scripts/test_geocoder.py "Darjeeling"

Expected (approximate):
  GeocodedPlace(name='Darjeeling', lat=27.041, lng=88.263)

Verify the cache actually works on the SECOND call (this replaces the v1 lru_cache.cache_info()
check, which no longer applies):
  python -c "
import asyncio
from src.geo import geocoder

async def main():
    geocoder._clear_cache_for_tests()
    r1 = await geocoder.geocode('Darjeeling')
    r2 = await geocoder.geocode('Darjeeling')
    assert r1 is not None and r2 is not None
    assert r1.lat == r2.lat and r1.lng == r2.lng
    stats = geocoder.cache_stats()
    assert stats['hits'] >= 1, f'expected a cache hit, got stats={stats}'
    print('Cache stats:', stats)
    print('PASS')

asyncio.run(main())
"

✅ Failure path 1 — network failure returns None (not raise):
  python -c "
import asyncio
from unittest.mock import AsyncMock, patch
import httpx
from src.geo.geocoder import geocode, _clear_cache_for_tests
async def main():
    with patch('src.geo.geocoder._fetch_nominatim', new_callable=AsyncMock, side_effect=httpx.ConnectError('down')):
        _clear_cache_for_tests()
        assert await geocode('Nowhereville XYZ') is None
    print('PASS — failure returns None')
asyncio.run(main())
"

✅ Failure path 2 — the specific v1 bug this step fixes: two sequential awaits on a cached
   result must both succeed (this is the exact scenario that crashed under lru_cache):
  python -c "
import asyncio
from src.geo.geocoder import geocode, _clear_cache_for_tests
async def main():
    _clear_cache_for_tests()
    r1 = await geocode('Darjeeling')
    r2 = await geocode('Darjeeling')  # would raise RuntimeError under the old lru_cache bug
    r3 = await geocode('Darjeeling')  # third call for extra confidence
    assert r1 and r2 and r3
    print('PASS — repeated awaits on cached async result do not raise')
asyncio.run(main())
"
```

---

## Step 2.2 — geo/overpass.py — POI scraper

```
Read AGENT.md before proceeding.

TASK: Implement the Overpass API gateway for POI scraping.
This is step 2.2. No new package installs.

─── IMPLEMENT src/geo/overpass.py ───

  🏗️ Gateway Pattern — callers never construct OverpassQL directly.

  OverpassQL template (radius in km → meters):
    [out:json][timeout:60];
    (
      node["tourism"~"attraction|viewpoint|museum|monastery"](around:{radius_m},{lat},{lng});
      way["tourism"~"attraction|viewpoint|museum|monastery"](around:{radius_m},{lat},{lng});
      node["leisure"="park"](around:{radius_m},{lat},{lng});
      node["highway"="trailhead"](around:{radius_m},{lat},{lng});
    );
    out center tags;

  _HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)

  def _category_from_tags(tags: dict) -> str:
      """Priority-ordered mapping per the locked P2 category table above."""

  def _element_to_poi(element: dict) -> RawPOI | None:
      """
      - Skip elements with no name tag (unnamed discarded)
      - lat/lng from element lat/lon OR center.lat/center.lon for ways
      - osm_id = f"{element['type']}/{element['id']}"
      - category from _category_from_tags(tags)
      - raw_tags = tags dict copy
      """

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=16),
         retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
  async def _post_overpass(query: str) -> dict:
      """POST to settings.OVERPASS_API_URL with query body. 4xx -> log + return {"elements": []}."""

  async def fetch_pois(lat: float, lng: float, radius_km: float) -> list[RawPOI]:
      """
      Public entry point.
      1. Build OverpassQL
      2. POST via _post_overpass
      3. Parse elements -> RawPOI, skip unnamed
      4. Deduplicate by osm_id (last wins)
      5. Return list (may be empty)
      """

─── CREATE scripts/test_overpass.py ───

  """CLI: python scripts/test_overpass.py <lat> <lng> <radius_km>"""
  # Default args if omitted: 27.041 88.263 30
  # Print: Fetched {n} POIs
  # Print first 3 POI names for sanity

─── RULES ───
- fetch_pois returns [] on any failure after retries — never raises to callers.
- No DB imports. No FastAPI imports.
- Deduplicate by osm_id before returning.

─── FAILURE BOUNDARY ───
Blueprint row: Overpass → tenacity 3x → return [].
Must NOT: abort caller, raise unhandled httpx errors, or write to DB.

─── VALIDATION ───
Run:
  python scripts/test_overpass.py 27.041 88.263 30

Expected:
  Fetched {n} POIs   (n >= 50 for Darjeeling; blueprint cites ~144)

✅ Failure path: mock _post_overpass to raise ConnectError — fetch_pois returns []:
  python -c "
import asyncio
from unittest.mock import AsyncMock, patch
import httpx
from src.geo.overpass import fetch_pois
async def main():
    with patch('src.geo.overpass._post_overpass', new_callable=AsyncMock, side_effect=httpx.ConnectError('down')):
        assert await fetch_pois(27.041, 88.263, 30) == []
    print('PASS — failure returns empty list')
asyncio.run(main())
"
```

---

## Step 2.3 — places/repository.py — upsert + radius + paginated

```
Read AGENT.md before proceeding.

TASK: Implement PlaceRepository with atomic PostGIS upsert, geography-based radius search,
and paginated list.
This is step 2.3. No new package installs.

─── IMPLEMENT src/places/repository.py ───

  import uuid
  from geoalchemy2 import Geography
  from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
  from sqlalchemy import cast, func, select
  from sqlalchemy.dialects.postgresql import insert
  from sqlalchemy.ext.asyncio import AsyncSession

  from src.core.database.base_repository import BaseRepository
  from src.core.pagination import PageParams
  from src.geo.schemas import RawPOI
  from src.places.models import Place

  class PlaceRepository(BaseRepository[Place, uuid.UUID]):

      async def upsert_from_poi(self, poi: RawPOI, destination_id: uuid.UUID) -> Place:
          """
          ⚠️ CONCURRENCY-CRITICAL (v2 rule): single atomic statement, no separate query-back.

          stmt = (
              insert(Place)
              .values(
                  osm_id=poi.osm_id,
                  name=poi.name,
                  category=poi.category,
                  tags=poi.raw_tags,
                  location=ST_SetSRID(ST_MakePoint(poi.lng, poi.lat), 4326),  # lng FIRST
                  destination_id=destination_id,
              )
              .on_conflict_do_update(
                  index_elements=[Place.osm_id],
                  set_=dict(
                      name=poi.name,
                      category=poi.category,
                      tags=poi.raw_tags,
                      location=ST_SetSRID(ST_MakePoint(poi.lng, poi.lat), 4326),
                      destination_id=destination_id,
                      updated_at=func.now(),
                  ),
              )
              .returning(Place)
          )
          result = await self.session.execute(stmt)
          place = result.scalar_one()
          Flush only — no commit. Return `place` directly from RETURNING — do NOT issue a
          second SELECT by osm_id. This halves DB round trips versus a separate query-back,
          which matters when seeding ~150 POIs per destination.
          """

      async def find_within_radius(
          self, lat: float, lng: float, radius_km: float, *, limit: int = 100
      ) -> list[Place]:
          """
          LOCKED (v2): always cast both sides to Geography — never bare geometry degrees.

          stmt = (
              select(Place)
              .where(
                  self._soft_delete_filter(),
                  ST_DWithin(
                      cast(Place.location, Geography),
                      cast(ST_SetSRID(ST_MakePoint(lng, lat), 4326), Geography),
                      radius_km * 1000,
                  ),
              )
              .limit(limit)
          )
          """

      async def list_by_destination(
          self, destination_id: uuid.UUID, params: PageParams
      ) -> tuple[list[Place], int]:
          """Delegate to list_paginated(filters={'destination_id': destination_id}, params=params)."""

      async def count_by_destination(self, destination_id: uuid.UUID) -> int:
          """COUNT non-deleted places for destination — used by seed script."""

─── RULES ───
- ST_MakePoint takes (longitude, latitude) — not (lat, lng).
- upsert_from_poi is a SINGLE atomic INSERT...ON CONFLICT...RETURNING statement — no
  separate lookup-then-insert, no separate query-back after the upsert.
- find_within_radius ALWAYS uses the Geography cast — this is not implementer's choice.
- Repository never commits — caller commits.
- Use SQLAlchemy 2.0 insert().on_conflict_do_update() — not raw string SQL.

─── FAILURE BOUNDARY ───
DB errors propagate to caller (seed script logs + continues per POI).
Must NOT: commit inside repository, swallow IntegrityError silently without log, or use a
check-then-act pattern that races under concurrent seeding.

─── VALIDATION ───
Run (this replaces the v1 script, which contained a non-runnable expression):
  python -c "
import asyncio, uuid
from geoalchemy2.shape import to_shape
from src.core.database.session import AsyncSessionLocal
from src.core.pagination import PageParams
from src.destinations.models import Destination
from src.geo.schemas import RawPOI
from src.places.repository import PlaceRepository

async def main():
    async with AsyncSessionLocal() as session:
        dest = Destination(name='Repo Test', country='IN', display_name='Repo Test, IN',
                           lat=27.04, lng=88.26, place_count=0, enriched_count=0, indexed_count=0)
        session.add(dest)
        await session.flush()

        repo = PlaceRepository(session)
        poi = RawPOI(osm_id='node/999999001', name='Test POI', lat=27.041, lng=88.263,
                     category='viewpoint', raw_tags={'tourism': 'viewpoint'})

        p1 = await repo.upsert_from_poi(poi, dest.id)
        p2 = await repo.upsert_from_poi(poi, dest.id)     # re-run — must update, not duplicate
        assert p1.id == p2.id, 'upsert must be idempotent'

        nearby = await repo.find_within_radius(27.04, 88.26, radius_km=5)
        assert any(x.id == p1.id for x in nearby), 'point should be found within 5km radius'

        far_away = await repo.find_within_radius(0.0, 0.0, radius_km=5)  # Gulf of Guinea
        assert not any(x.id == p1.id for x in far_away), 'point should NOT match a distant radius'

        items, total = await repo.list_by_destination(dest.id, PageParams(page=1, size=10))
        assert total >= 1 and items[0].name == 'Test POI'

        shape = to_shape(p1.location)
        assert abs(shape.y - 27.041) < 0.001

        await session.rollback()
        print('PASS — upsert, geography-based radius, paginate OK')

asyncio.run(main())
"

✅ Failure path — concurrent upsert of the SAME new osm_id must not raise IntegrityError
   (proves the atomic ON CONFLICT actually protects against the race):
  python -c "
import asyncio
from src.core.database.session import AsyncSessionLocal
from src.destinations.models import Destination
from src.geo.schemas import RawPOI
from src.places.repository import PlaceRepository

async def main():
    async with AsyncSessionLocal() as session:
        dest = Destination(name='Race Test', country='IN', display_name='Race Test, IN',
                           lat=27.04, lng=88.26, place_count=0, enriched_count=0, indexed_count=0)
        session.add(dest)
        await session.flush()

        poi = RawPOI(osm_id='node/999999002', name='Race POI', lat=27.05, lng=88.27,
                     category='attraction', raw_tags={})

        repo1 = PlaceRepository(session)
        repo2 = PlaceRepository(session)

        # Same session, two 'concurrent-style' calls — both must succeed (ON CONFLICT handles it),
        # a check-then-insert pattern would raise on the second call in true concurrent conditions.
        r1 = await repo1.upsert_from_poi(poi, dest.id)
        r2 = await repo2.upsert_from_poi(poi, dest.id)
        assert r1.id == r2.id
        await session.rollback()
        print('PASS — no IntegrityError on repeated upsert of same osm_id')

asyncio.run(main())
"
```

---

## Step 2.6a — destinations/schemas.py + destinations/exceptions.py

```
Read AGENT.md before proceeding.

TASK: Implement destination Pydantic schemas and domain exceptions.
This is step 2.6a — schemas and exceptions only. No HTTP or DB logic.

─── IMPLEMENT src/destinations/schemas.py ───

  import uuid
  from datetime import datetime
  from typing import Literal
  from pydantic import BaseModel, ConfigDict, Field

  class DestinationOut(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      id: uuid.UUID
      name: str
      country: str
      display_name: str
      lat: float
      lng: float
      place_count: int = 0
      created_at: datetime

  class DestinationSearchQuery(BaseModel):
      q: str = Field(min_length=2, max_length=200)

  class DestinationReadinessOut(BaseModel):
      destination_id: uuid.UUID
      score: float
      tier: Literal["ready", "limited", "sparse"]
      place_count: int
      enriched_pct: float
      indexed_pct: float
      message: str | None = None

─── IMPLEMENT src/destinations/exceptions.py ───

  from src.core.exceptions import NotFoundError

  class DestinationNotFoundError(NotFoundError):
      def __init__(self, query: str | None = None, destination_id: str | None = None):
          details = {}
          if query:
              details["query"] = query
          if destination_id:
              details["destination_id"] = destination_id
          super().__init__(message="Destination not found", details=details or None)

─── RULES ───
- Schemas have no imports from models, repository, or geo.
- DestinationNotFoundError status_code 404 via NotFoundError parent.

─── VALIDATION ───
  python -c "
from src.destinations.schemas import DestinationOut, DestinationReadinessOut
from src.destinations.exceptions import DestinationNotFoundError
e = DestinationNotFoundError(query='Atlantis')
assert e.status_code == 404
print('PASS')
"
```

---

## Step 2.6b — destinations/repository.py + destinations/service.py

```
Read AGENT.md before proceeding.

TASK: Implement DestinationRepository with an ATOMIC upsert (fixes the v1 race condition)
and DestinationService with cache-aside search.
This is step 2.6b. No new package installs.

─── IMPLEMENT src/destinations/repository.py ───

  import uuid
  from sqlalchemy import func, select
  from sqlalchemy.dialects.postgresql import insert
  from sqlalchemy.ext.asyncio import AsyncSession

  from src.core.database.base_repository import BaseRepository
  from src.destinations.models import Destination
  from src.geo.schemas import GeocodedPlace

  class DestinationRepository(BaseRepository[Destination, uuid.UUID]):

      async def get_by_osm_place_id(self, osm_place_id: str) -> Destination | None:
          stmt = select(Destination).where(Destination.osm_place_id == osm_place_id)
          return (await self.session.execute(stmt)).scalar_one_or_none()

      async def search_by_name(self, query: str, *, limit: int = 10) -> list[Destination]:
          """
          ILIKE on name OR display_name (case-insensitive).
          query sanitized — strip whitespace.
          Order by place_count desc, then name.
          """

      async def upsert_from_geocoded(self, geocoded: GeocodedPlace) -> Destination:
          """
          ⚠️ FIXES v1 RACE CONDITION: this MUST be a single atomic statement, not a
          get_by_osm_place_id() lookup followed by a separate create(). Two concurrent
          cache-misses on the same new destination will otherwise both pass the lookup
          and both attempt an insert — the second raises IntegrityError on the unique
          osm_place_id constraint, surfacing as an unhandled 500.

          LOCKED (v2): the ON CONFLICT SET clause updates ONLY geocode-derived fields.
          It must NEVER include place_count / enriched_count / indexed_count — those
          are owned exclusively by seed/enrich/index scripts (see P2 design decisions).

          stmt = (
              insert(Destination)
              .values(
                  name=geocoded.name,
                  country=geocoded.country,
                  display_name=geocoded.display_name,
                  osm_place_id=geocoded.osm_place_id,
                  lat=geocoded.lat,
                  lng=geocoded.lng,
                  place_count=0,
                  enriched_count=0,
                  indexed_count=0,
              )
              .on_conflict_do_update(
                  index_elements=[Destination.osm_place_id],
                  set_=dict(
                      name=geocoded.name,
                      country=geocoded.country,
                      display_name=geocoded.display_name,
                      lat=geocoded.lat,
                      lng=geocoded.lng,
                      updated_at=func.now(),
                      # place_count / enriched_count / indexed_count deliberately absent
                  ),
              )
              .returning(Destination)
          )
          result = await self.session.execute(stmt)
          return result.scalar_one()

          Flush only — caller (service) commits.
          """

─── IMPLEMENT src/destinations/service.py ───

  class DestinationService:
      def __init__(self, session: AsyncSession): ...

      async def search(self, query: str) -> list[Destination]:
          """
          🏗️ Cache-Aside:
          1. repo.search_by_name(query) — if results: return
          2. geocoded = await geocode(query) — if None: raise DestinationNotFoundError(query=query)
          3. dest = await repo.upsert_from_geocoded(geocoded)   # atomic — safe under concurrency
          4. await session.commit(); await session.refresh(dest)
          5. return [dest]
          """
          # Import geocode from src.geo.geocoder only here (service layer), not in router.

      async def get_by_id(self, destination_id: uuid.UUID) -> Destination:
          """get_by_id_or_raise → DestinationNotFoundError if missing."""

─── RULES ───
- search() commits after the Nominatim-miss path (standalone operation, like AuthService).
- DB hit path does not call geocode.
- Service never imports httpx — only geo.geocode.
- upsert_from_geocoded is ALWAYS the atomic ON CONFLICT form — never lookup-then-create.

─── FAILURE BOUNDARY ───
geocode None → DestinationNotFoundError 404 at API layer.
Concurrent misses on the same new destination → both succeed, no IntegrityError, no 500.
Must NOT: call Nominatim from repository, return 502 for geocode miss (404 is correct).

─── VALIDATION ───
  python -c "
import asyncio
from src.core.database.session import AsyncSessionLocal
from src.destinations.service import DestinationService
async def main():
    async with AsyncSessionLocal() as session:
        svc = DestinationService(session)
        results = await svc.search('Darjeeling')
        assert len(results) >= 1
        assert results[0].place_count >= 0
        # Second search — DB hit
        results2 = await svc.search('Darjeeling')
        assert results2[0].id == results[0].id
        print('PASS:', results[0].name, results[0].id)
asyncio.run(main())
"

✅ Failure path — the exact v1 race, exercised directly against the repository (proves the
   atomic statement, not the service-level cache-aside check, is what prevents the crash):
  python -c "
import asyncio
from src.core.database.session import AsyncSessionLocal
from src.destinations.repository import DestinationRepository
from src.geo.schemas import GeocodedPlace

async def main():
    async with AsyncSessionLocal() as session:
        repo = DestinationRepository(session)
        geocoded = GeocodedPlace(
            name='Race Town', lat=10.0, lng=20.0,
            osm_place_id='relation/race-test-1', country='XX', display_name='Race Town, XX',
        )
        # Simulate two 'concurrent' misses hitting upsert back-to-back before either commits.
        d1 = await repo.upsert_from_geocoded(geocoded)
        d2 = await repo.upsert_from_geocoded(geocoded)   # v1 bug: this would raise IntegrityError
        assert d1.id == d2.id
        await session.rollback()
        print('PASS — atomic upsert survives repeated calls with no IntegrityError')

asyncio.run(main())
"
```

---

## Step 2.4 — scripts/seed_destination.py

```
Read AGENT.md before proceeding.

TASK: Implement the destination seed CLI — geocode → Overpass → upsert places + Destination row.
Depends on 2.6b's DestinationRepository (already built per the canonical order above).
This is step 2.4. No new package installs.

─── IMPLEMENT scripts/seed_destination.py ───

  """
  Seed a destination with POIs from Overpass.
  Usage: python scripts/seed_destination.py --destination "Darjeeling" --radius 30
  Re-runnable (upsert). Commits on success.
  """
  import argparse, asyncio
  from src.geo.geocoder import geocode
  from src.geo.overpass import fetch_pois
  from src.core.database.session import AsyncSessionLocal
  from src.destinations.repository import DestinationRepository
  from src.places.repository import PlaceRepository

  Flow:
    1. geocode(destination_name) → GeocodedPlace | exit 1 with message if None
    2. dest = await DestinationRepository(session).upsert_from_geocoded(geocoded)  # atomic
    3. fetch_pois(dest.lat, dest.lng, radius_km)
    4. For each POI (enumerate) — extract this loop as an importable
       `async def seed_places(session, destination_id, pois) -> int` (step 2.9 tests it directly):
         try:
             async with session.begin_nested():        # SAVEPOINT per POI — see rule below
                 await PlaceRepository(session).upsert_from_poi(poi, dest.id)
         except Exception as e: log.warning("seed.poi_failed", osm_id=poi.osm_id, error=str(e)); continue
         if (i+1) % 10 == 0: print progress
    5. Update destination.place_count = success_count (enriched_count/indexed_count unchanged —
       repository.update({"place_count": success_count}), NOT a raw setattr that would need
       another flush path; use the existing BaseRepository.update() method)
    6. session.commit()
    7. Print: Seeded {success}/{total} places for {name} (id={dest_id})

─── RULES ───
- Single POI failure → log + continue. Never abort full seed for one bad record.
- Each POI upsert runs inside `async with session.begin_nested()` (SAVEPOINT). A plain
  try/except is NOT enough: a DB-level error aborts the whole Postgres transaction, so every
  subsequent POI would then fail too and the final commit would raise. The savepoint rolls
  back only the failed row and keeps the batch alive — this is what makes "log + continue" real.
- geocode None → exit code 1, human-readable error (do not commit).
- Overpass [] → commit destination with place_count=0, print warning.
- Script calls geo/ and repositories — not httpx directly.
- Uses DestinationRepository.upsert_from_geocoded (the atomic v2 version) — never a manual
  lookup-then-create block inline in the script.

─── FAILURE BOUNDARY ───
Blueprint: Overpass fail → []. Seed logs warning, destination row still saved with 0 places.
Single POI failure → logged, batch continues, final count reflects successes only.
Must NOT: exit 1 on partial POI failures, call Overpass outside geo/, abort the whole batch
because one POI's insert raised.

─── VALIDATION ───
Run:
  python scripts/seed_destination.py --destination "Darjeeling" --radius 30

Expected:
  Seeded {n}/{n} places for Darjeeling   (n >= 50; often ~100–150)
  Final line includes destination UUID

Re-run (idempotent):
  python scripts/seed_destination.py --destination "Darjeeling" --radius 30

Expected: same destination id, no duplicate places (count stable).

✅ Failure path 1 — geocode nonsense → exit 1:
  python scripts/seed_destination.py --destination "XyzzyNonexistentPlace99999"
  Expected: non-zero exit, no commit (or destination not created)

✅ Failure path 2 — a single bad POI must not abort the whole seed (mocked, no network needed;
   this is the test that was MISSING in v1 — see Step 2.9 for the pytest version of this).
   NOTE (v2.1): `patch.object` replaces an *instance method*, so the replacement must accept
   `self` as its first parameter. Without it, `poi` binds to the repository instance and every
   POI fails — the snippet reports 0 successes and the assertion misleadingly looks like a
   product bug rather than a test bug.
  python -c "
import asyncio
from unittest.mock import patch
from src.geo.schemas import RawPOI
from src.places.repository import PlaceRepository

async def main():
    good_poi = RawPOI(osm_id='node/1', name='Good', lat=1.0, lng=1.0, category='attraction', raw_tags={})
    bad_poi  = RawPOI(osm_id='node/2', name='Bad',  lat=1.0, lng=1.0, category='attraction', raw_tags={})

    success = 0
    pois = [good_poi, bad_poi, good_poi]
    call_count = {'n': 0}

    async def flaky_upsert(self, poi, dest_id):
        call_count['n'] += 1
        if poi.osm_id == 'node/2':
            raise RuntimeError('simulated DB error on this POI')
        return object()

    with patch.object(PlaceRepository, 'upsert_from_poi', new=flaky_upsert):
        repo = PlaceRepository.__new__(PlaceRepository)  # bypass __init__, only testing the loop pattern
        for poi in pois:
            try:
                await repo.upsert_from_poi(poi, 'dest-id')
                success += 1
            except Exception:
                continue

    assert success == 2, f'expected 2 successes out of 3 (1 simulated failure), got {success}'
    assert call_count['n'] == 3
    print('PASS — batch survives a single POI failure, continues to completion')

asyncio.run(main())
"

✅ Failure path 3 — same contract against the REAL seed loop and a real transaction (this is
   the one that actually proves the savepoint rule; the mocked snippet above only proves the
   try/except shape). Requires Postgres:
  python -c "
import asyncio
from unittest.mock import patch
from scripts.seed_destination import seed_places
from src.core.database.session import AsyncSessionLocal
from src.destinations.models import Destination
from src.geo.schemas import RawPOI
from src.places.repository import PlaceRepository

original = PlaceRepository.upsert_from_poi

async def flaky(self, poi, dest_id):
    if poi.osm_id == 'node/999999902':
        raise RuntimeError('simulated DB error')
    return await original(self, poi, dest_id)

async def main():
    async with AsyncSessionLocal() as session:
        dest = Destination(name='Seed Loop Test', country='IN', display_name='Seed Loop Test, IN',
                           osm_place_id='node/seed-loop-test', lat=27.04, lng=88.26,
                           place_count=0, enriched_count=0, indexed_count=0)
        session.add(dest)
        await session.flush()

        pois = [RawPOI(osm_id=f'node/99999990{i}', name=f'P{i}', lat=27.04, lng=88.26,
                       category='attraction', raw_tags={}) for i in (1, 2, 3)]

        with patch.object(PlaceRepository, 'upsert_from_poi', new=flaky):
            success = await seed_places(session, dest.id, pois)

        assert success == 2, f'expected 2 successes, got {success}'
        assert await PlaceRepository(session).count_by_destination(dest.id) == 2
        await session.rollback()
        print('PASS — bad POI rolled back to its savepoint, batch and transaction survive')

asyncio.run(main())
"
```

---

## Step 2.5 — geo/osrm.py — routing client

```
Read AGENT.md before proceeding.

TASK: Implement the OSRM routing gateway with haversine × 1.4 fallback.
This is step 2.5. No new package installs. Has no P2 dependents — can be built any time
after 2.3, but stays in canonical sequence here.

─── IMPLEMENT src/geo/osrm.py ───

  import math
  from src.geo.schemas import RouteResult
  from src.config import get_settings

  _HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
  _HAVERSINE_ROAD_FACTOR = 1.4
  _AVG_SPEED_KMH = 30.0  # for fallback duration estimate

  def _haversine_km(lat1, lng1, lat2, lng2) -> float: ...

  def _fallback_route(waypoints: list[tuple[float, float]]) -> RouteResult:
      """Sum haversine legs × 1.4; duration from distance / AVG_SPEED; fallback_used=True; log warning."""

  @retry(stop=stop_after_attempt(2), wait=wait_fixed(1),
         retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
  async def _call_osrm(waypoints: list[tuple[float, float]]) -> dict | None:
      """
      GET {OSRM_BASE_URL}/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=polyline
      Waypoints are (lat, lng) tuples — convert to lng,lat for URL.
      """

  async def get_route(waypoints: list[tuple[float, float]]) -> RouteResult:
      """
      Require len(waypoints) >= 2 else ValueError.
      Try OSRM → on failure or empty routes → _fallback_route.
      Never raises httpx errors to callers.
      Map OSRM: distance meters → km, duration seconds → minutes, geometry → encoded_polyline.
      """

─── FAILURE BOUNDARY ───
Blueprint: OSRM → tenacity 2x → haversine × 1.4. Never fails user request.
Must NOT: raise to caller on network failure, return distance_km=0 without fallback_used=True.

─── VALIDATION ───
Run:
  python -c "
import asyncio
from src.geo.osrm import get_route
async def main():
    r = await get_route([(27.04, 88.26), (27.03, 88.27)])
    print('distance_km:', r.distance_km, 'fallback:', r.fallback_used)
    assert r.distance_km > 0
    print('PASS')
asyncio.run(main())
"

✅ Failure path: mock _call_osrm to return None — get_route uses fallback:
  python -c "
import asyncio
from unittest.mock import AsyncMock, patch
from src.geo.osrm import get_route
async def main():
    with patch('src.geo.osrm._call_osrm', new_callable=AsyncMock, return_value=None):
        r = await get_route([(27.04, 88.26), (27.03, 88.27)])
        assert r.fallback_used is True and r.distance_km > 0
    print('PASS — haversine fallback')
asyncio.run(main())
"
```

---

## Step 2.6c — destinations/router.py + Register in main.py

```
Read AGENT.md before proceeding.

TASK: Wire destinations HTTP routes and register router in main.py.
This is step 2.6c.

─── IMPLEMENT src/destinations/router.py ───

  router = APIRouter(prefix="/api/v1/destinations", tags=["destinations"])

  @router.get("/search")
  async def search_destinations(
      q: str = Query(min_length=2, max_length=200),
      db: AsyncSession = Depends(get_db),
  ) -> ApiResponse[list[DestinationOut]]:
      """DB-first search with Nominatim cache-aside fallback."""
      results = await DestinationService(db).search(q)
      return ApiResponse(data=[DestinationOut.model_validate(d) for d in results])

  @router.get("/{destination_id}/readiness")
  async def get_destination_readiness(
      destination_id: uuid.UUID,
      db: AsyncSession = Depends(get_db),
  ) -> ApiResponse[DestinationReadinessOut]:
      return ApiResponse(data=await DestinationService(db).get_readiness(destination_id))
      # (get_readiness implemented in step 2.8 — stub or wire after that step)

─── UPDATE src/main.py ───
  from src.destinations.router import router as destinations_router
  app.include_router(destinations_router)

─── RULES ───
- No auth required on search (public catalog).
- Router calls DestinationService only.
- Return ApiResponse[list[DestinationOut]].

─── FAILURE BOUNDARY ───
Unknown destination → 404 ErrorResponse, not 500.
Must NOT: import geocode in router.

─── VALIDATION ───
Start server: uvicorn src.main:app --reload --port 8000

  curl -s "http://localhost:8000/api/v1/destinations/search?q=Darjeeling" | python -m json.tool

Expected: success true, data array with at least one destination, lat/lng populated.

Second request — no new Nominatim call (DB cache):
  curl -s "http://localhost:8000/api/v1/destinations/search?q=Darjeeling" | python -m json.tool

✅ Failure path:
  curl -s "http://localhost:8000/api/v1/destinations/search?q=XyzzyNonexistent999" | python -m json.tool
  Expected: 404, code not_found
```

---

## Step 2.6c′ — Endpoint-specific rate limit for /destinations/search ★ NEW (v2)

```
Read AGENT.md before proceeding.

TASK: Extend P1's RateLimitMiddleware so /destinations/search has its own, tighter limit
than the generic 60/min/IP default. Every cache-miss on this endpoint costs a live Nominatim
call — a shared public resource — so this route needs its own throttle, not just the default.
This is step 2.6c′. No new package installs.

─── ADD to src/config.py (and .env.example) ───

  RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS: int = 20
  RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS: int = 60
  RATE_LIMIT_DESTINATIONS_SEARCH_PATH: str = "/api/v1/destinations/search"

─── EXTEND src/core/middleware/rate_limit.py ───

  P1 built `_resolve_limits(path)` as a single if/else for the planner path. Generalize it
  to a small ordered table so P2 (and future phases) can register more path-specific limits
  without rewriting the function each time:

  def _route_limit_table() -> list[tuple[str, int, int]]:
      """
      Ordered (path, limit, window) table, most specific first. Built from settings so
      nothing is hardcoded outside get_settings() (AGENT.md rule).
      """
      settings = get_settings()
      return [
          (settings.RATE_LIMIT_PLANNER_PATH, settings.RATE_LIMIT_PLANNER_REQUESTS,
           settings.RATE_LIMIT_PLANNER_WINDOW_SECONDS),
          (settings.RATE_LIMIT_DESTINATIONS_SEARCH_PATH, settings.RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS,
           settings.RATE_LIMIT_DESTINATIONS_SEARCH_WINDOW_SECONDS),
      ]

  def _resolve_limits(path: str) -> tuple[int, int]:
      """
      Exact-match lookup against the route table; falls back to the global default
      (RATE_LIMIT_DEFAULT_REQUESTS / _WINDOW_SECONDS) if no specific rule matches.
      """
      for route_path, limit, window in _route_limit_table():
          if path == route_path:
              return limit, window
      settings = get_settings()
      return settings.RATE_LIMIT_DEFAULT_REQUESTS, settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS

─── RULES ───
- Do not change the fail-open behavior from P1 — limiter errors still allow the request.
- No hardcoded route strings outside get_settings() — the path constants live in config.py.
- This must be a backward-compatible EXTENSION of P1's function signature — existing tests
  from tests/core/test_middleware.py (step 1.11) must still pass unmodified.

─── FAILURE BOUNDARY ───
Limiter internal error → fail open (inherited from P1, unchanged).
Must NOT: apply the destinations-search limit to any other path, or regress the planner
route's existing 10/min limit.

─── VALIDATION ───
  python -c "
from src.config import get_settings
from src.core.middleware.rate_limit import _resolve_limits
s = get_settings()

# Destinations search gets its own, tighter limit
limit, window = _resolve_limits(s.RATE_LIMIT_DESTINATIONS_SEARCH_PATH)
assert limit == 20 and window == 60, f'got {limit}/{window}'

# Planner route limit from P1 is unaffected
limit2, window2 = _resolve_limits(s.RATE_LIMIT_PLANNER_PATH)
assert limit2 == 10 and window2 == 60

# Unrelated path falls back to the global default
limit3, window3 = _resolve_limits('/api/v1/health')
assert limit3 == s.RATE_LIMIT_DEFAULT_REQUESTS

print('PASS — destinations/search:', limit, '/', window, '| planner unaffected:', limit2, '/', window2)
"

Live check (server running):
  curl -si "http://localhost:8000/api/v1/destinations/search?q=Darjeeling" | Select-String -Pattern "x-ratelimit-limit" -CaseSensitive:$false

Expected: x-ratelimit-limit: 20   (not 60 — proves the path-specific rule is active)

✅ Failure path — 21st rapid request in the window returns 429:
  for /l %i in (1,1,21) do curl -s -o nul -w "%{http_code}\n" "http://localhost:8000/api/v1/destinations/search?q=Test%i"
  # PowerShell equivalent: 1..21 | ForEach-Object { curl -s -o $null -w "%{http_code}`n" "http://localhost:8000/api/v1/destinations/search?q=Test$_" }

Expected: first 20 responses 200 or 404 (depending on query), 21st is 429 with Retry-After header.
```

---

## Step 2.7a — places/schemas.py + places/service.py

```
Read AGENT.md before proceeding.

TASK: Implement PlaceOut schema and PlaceService — with a MANDATORY destination-existence
check (locked in v2; this was previously marked "optional").
This is step 2.7a.

─── IMPLEMENT src/places/schemas.py ───

  class PlaceOut(BaseModel):
      model_config = ConfigDict(from_attributes=True)
      id: uuid.UUID
      osm_id: str
      name: str
      category: str
      tags: dict
      summary: str | None
      lat: float          # extracted from geometry — NOT stored column
      lng: float
      destination_id: uuid.UUID
      created_at: datetime

      @classmethod
      def from_place(cls, place: Place) -> PlaceOut:
          """Use geoalchemy2.shape.to_shape(place.location) → .y=lat, .x=lng"""

─── IMPLEMENT src/places/service.py ───

  from src.destinations.repository import DestinationRepository

  class PlaceService:
      def __init__(self, session: AsyncSession):
          self.session = session
          self.repo = PlaceRepository(session)
          self.dest_repo = DestinationRepository(session)

      async def list_by_destination(
          self, destination_id: uuid.UUID, params: PageParams
      ) -> tuple[list[PlaceOut], int]:
          """
          LOCKED (v2): destination existence check is MANDATORY, not optional.
          1. await self.dest_repo.get_by_id_or_raise(destination_id)  # raises DestinationNotFoundError (404)
          2. places, total = await self.repo.list_by_destination(destination_id, params)
          3. return [PlaceOut.from_place(p) for p in places], total
          """

      async def get_by_id(self, place_id: uuid.UUID) -> PlaceOut:
          """get_by_id_or_raise on Place repo → PlaceOut.from_place"""

─── RULES ───
- PlaceOut lat/lng derived from geometry at serialization time.
- Service uses PlaceRepository for places and DestinationRepository ONLY for the existence
  check — it does not duplicate destination logic.
- The existence check happens BEFORE the paginated query — a request against a garbage
  destination_id must 404, never silently return total=0.

─── FAILURE BOUNDARY ───
Unknown destination_id → DestinationNotFoundError (404) — same behavior as
/destinations/{id}/readiness, consistent across the whole domain.
Must NOT: return total=0 for a nonexistent destination.

─── VALIDATION ───
Requires seeded Darjeeling from step 2.4. Use destination_id from seed output.

  python -c "
import asyncio, uuid
from src.core.database.session import AsyncSessionLocal
from src.core.pagination import PageParams
from src.destinations.repository import DestinationRepository
from src.destinations.exceptions import DestinationNotFoundError
from src.places.service import PlaceService

async def main():
    async with AsyncSessionLocal() as session:
        dests = await DestinationRepository(session).search_by_name('Darjeeling', limit=1)
        assert dests, 'Run seed_destination.py first'
        items, total = await PlaceService(session).list_by_destination(dests[0].id, PageParams(page=1, size=5))
        assert total >= 1
        assert items[0].lat != 0
        print('PASS', total, 'places')

        # ✅ Failure path — garbage destination_id must 404, not return total=0
        try:
            await PlaceService(session).list_by_destination(uuid.uuid4(), PageParams(page=1, size=5))
            assert False, 'expected DestinationNotFoundError'
        except DestinationNotFoundError:
            print('PASS — garbage destination_id raises 404, not a silent empty page')

asyncio.run(main())
"
```

---

## Step 2.7b — places/router.py + Register in main.py

```
Read AGENT.md before proceeding.

TASK: Wire places HTTP routes.
This is step 2.7b.

─── IMPLEMENT src/places/router.py ───

  router = APIRouter(prefix="/api/v1/places", tags=["places"])

  @router.get("")
  async def list_places(
      destination_id: uuid.UUID,
      params: PageParams = Depends(),
      db: AsyncSession = Depends(get_db),
  ) -> PaginatedResponse[PlaceOut]:
      items, total = await PlaceService(db).list_by_destination(destination_id, params)
      return paginate(items, total, params)

  @router.get("/{place_id}")
  async def get_place(
      place_id: uuid.UUID,
      db: AsyncSession = Depends(get_db),
  ) -> ApiResponse[PlaceOut]:
      return ApiResponse(data=await PlaceService(db).get_by_id(place_id))

─── UPDATE src/main.py ───
  from src.places.router import router as places_router
  app.include_router(places_router)

─── FAILURE BOUNDARY ───
Unknown place_id → 404 NotFoundError.
Unknown destination_id on the list endpoint → 404 DestinationNotFoundError (from 2.7a).
Must NOT: return raw Place ORM model, or return an empty page for a nonexistent destination.

─── VALIDATION ───
Use DESTINATION_ID and PAGE from seeded data:

  curl -s "http://localhost:8000/api/v1/places?destination_id={DESTINATION_ID}&page=2&size=10" | python -m json.tool

Expected:
  total >= 50, page=2, pages>=5, has_next=true, items length 10

  curl -s "http://localhost:8000/api/v1/places/{PLACE_ID}" | python -m json.tool

✅ Failure path 1 — unknown place:
  curl -s "http://localhost:8000/api/v1/places/00000000-0000-0000-0000-000000000001" -w "\n%{http_code}"
  Expected: 404

✅ Failure path 2 — unknown destination on the list endpoint (this is the newly-locked behavior):
  curl -s "http://localhost:8000/api/v1/places?destination_id=00000000-0000-0000-0000-000000000001&page=1" -w "\n%{http_code}"
  Expected: 404 with code "not_found" — NOT 200 with an empty items array
```

---

## Step 2.8 — destinations/readiness.py + GET /{id}/readiness

```
Read AGENT.md before proceeding.

TASK: Implement pure readiness scoring and the readiness HTTP endpoint.
This is step 2.8.

─── IMPLEMENT src/destinations/readiness.py ───

  from dataclasses import dataclass
  from typing import Literal

  PLACE_TARGET = 100

  @dataclass(frozen=True)
  class ReadinessResult:
      score: float
      tier: Literal["ready", "limited", "sparse"]
      place_count: int
      enriched_pct: float
      indexed_pct: float
      message: str | None

  def compute_readiness(
      place_count: int,
      enriched_count: int,
      indexed_count: int,
      search_available: bool,
  ) -> ReadinessResult:
      """
      Pure function — no I/O. Formula in the locked P2 design decisions section above.
      Messages:
        sparse: "Very limited POI data — results may be generic"
        limited: "Limited enrichment — semantic search not yet available" (when enriched_pct < 0.5)
        ready: None
      """

─── EXTEND src/destinations/service.py ───

  async def get_readiness(self, destination_id: uuid.UUID) -> DestinationReadinessOut:
      """
      1. Load destination or raise DestinationNotFoundError
      2. search_available = False  # P2: Qdrant wired in P3
      3. result = compute_readiness(dest.place_count, dest.enriched_count, dest.indexed_count, search_available)
      4. Return DestinationReadinessOut(destination_id=..., **result fields)
      """

─── RULES ───
- readiness.py has zero imports from SQLAlchemy, FastAPI, httpx, qdrant.
- P2: always search_available=False → indexed_pct=0 in output.
- Endpoint returns 200 even when Qdrant unavailable (indexed_pct=0).

─── FAILURE BOUNDARY ───
Blueprint: Qdrant unavailable → indexed_pct=0, score still computed, 200 response.
Must NOT: call Qdrant in P2, fail endpoint when indexed_count=0.

─── VALIDATION ───
After seeding Darjeeling:

  curl -s "http://localhost:8000/api/v1/destinations/{DESTINATION_ID}/readiness" | python -m json.tool

Expected (P2, pre-enrichment):
  score >= 0.35 and < 0.7
  tier: "limited"
  place_count >= 50
  enriched_pct: 0.0
  indexed_pct: 0.0

Unit test readiness math:
  python -c "
from src.destinations.readiness import compute_readiness
r = compute_readiness(144, 0, 0, False)
assert r.tier == 'limited' and 0.35 <= r.score <= 0.45
r2 = compute_readiness(144, 100, 100, True)
assert r2.tier == 'ready' and r2.score >= 0.7
print('PASS', r.score, r.tier)
"

✅ Failure path:
  curl -s "http://localhost:8000/api/v1/destinations/00000000-0000-0000-0000-000000000001/readiness" -w "\n%{http_code}"
  Expected: 404
```

---

## Step 2.9 — P2 pytest coverage (expanded in v2)

```
Read AGENT.md before proceeding.

TASK: Add pytest tests for geo gateways (mocked), readiness math, atomic upserts under
races, and new API routes — including the previously-missing seed partial-failure test.
This is step 2.9. No new package installs.

─── CREATE tests/geo/test_geocoder.py ───
  - test_geocode_success (mock _fetch_nominatim)
  - test_geocode_failure_returns_none (mock ConnectError)
  - ★ NEW test_geocode_cache_hit_on_repeated_call — asserts a second call to geocode() with
    the same query does NOT invoke _fetch_nominatim again, AND that the coroutine can be
    awaited twice without RuntimeError (regression test for the v1 lru_cache bug).
  - ★ NEW test_geocode_caches_none_result_too — mock _fetch_nominatim to return [] once;
    assert two calls only invoke _fetch_nominatim once (a confirmed miss is also cached).

─── CREATE tests/geo/test_overpass.py ───
  - test_fetch_pois_deduplicates (mock _post_overpass fixture JSON)
  - test_fetch_pois_failure_returns_empty

─── CREATE tests/geo/test_osrm.py ───
  - test_get_route_fallback_when_osrm_none

─── CREATE tests/destinations/test_readiness.py ───
  - test_compute_readiness_sparse (0 places)
  - test_compute_readiness_limited (144 places, 0 enriched)
  - test_compute_readiness_ready (144 places, 100 enriched, 100 indexed, search_available=True)

─── CREATE tests/destinations/test_destinations_repository.py ★ NEW ───
  - test_upsert_from_geocoded_is_idempotent — call upsert_from_geocoded twice with the same
    osm_place_id in the same db_session, assert same destination id, no exception raised.
  - test_upsert_from_geocoded_does_not_reset_counters — seed a destination with place_count=50,
    call upsert_from_geocoded again with the same osm_place_id, assert place_count is still 50
    (regression test for the "ON CONFLICT SET must not touch counters" rule).

─── CREATE tests/destinations/test_destinations_router.py ───
  - test_search_returns_list (mock DestinationService or seed fixture)
  - test_search_not_found_404 (mock geocode None)
  - test_readiness_endpoint (seed destination in db_session)
  - ★ NEW test_search_rate_limit_is_path_specific — mock get_rate_limiter().is_allowed to
    return (False, 0) only when called with a key containing the destinations/search path;
    assert /destinations/search gets 429 while /api/v1/health on the same client remains 200.

─── CREATE tests/places/test_places_router.py ───
  - test_list_places_paginated (insert destination + places in db_session)
  - test_get_place_404
  - ★ NEW test_list_places_unknown_destination_404 — call with a random UUID, assert 404
    with code "not_found", NOT a 200 with an empty items array (regression test for the
    previously-optional existence check).

─── CREATE tests/places/test_places_repository.py ★ NEW ───
  - test_find_within_radius_respects_geography_units — insert a place ~3km from a query
    point; assert it IS found with radius_km=5 and IS NOT found with radius_km=1. This is
    the regression test for the locked geography-cast decision: a bug that reverted to
    plain-geometry degree units would make this test fail obviously (either everything
    matches, or nothing does).

─── CREATE tests/scripts/test_seed_destination.py ★ NEW (fills the v1 gap) ───

  """
  Tests the seed script's per-POI failure-tolerance contract directly, without touching
  the network. This is the missing test flagged in v1 review — the blueprint's hard rule
  ("single POI failure -> log + continue, never abort the batch") had zero coverage.
  """

  async def test_seed_survives_partial_poi_failure(db_session, mocker):
      """
      Arrange: 3 POIs, the middle one's upsert_from_poi raises.
      Act: run the seed script's per-POI loop (import and call the actual loop function,
           refactored out of __main__ if necessary so it's testable in isolation —
           e.g. `async def seed_places(session, dest_id, pois) -> int` returning success count).
      Assert: success count == 2 (not 3, not 0 — the batch didn't abort, and the bad one
              didn't silently count as success).
      """

  async def test_seed_continues_when_overpass_returns_empty(db_session, mocker):
      """
      Mock fetch_pois to return []. Assert the destination is still created/updated with
      place_count == 0, and the script does not raise or exit non-zero for this case
      (only a geocode failure should exit non-zero, per the failure boundary table).
      """

─── RULES ───
- Mock external HTTP in unit tests — do not hit Nominatim/Overpass/OSRM in CI.
- Use existing db_session fixture from tests/conftest.py.
- Tests that need places: insert Destination + Place rows with from_shape(Point(lng, lat)).
- If the seed script's per-POI loop isn't already an importable function, refactor it out
  of the `if __name__ == "__main__":` block now — untestable inline loops are not acceptable
  for a batch operation with a hard resilience contract attached to it.

─── VALIDATION ───
  python -m pytest tests/geo tests/destinations tests/places tests/scripts -v

Expected: all new tests pass, including the four ★ NEW regression tests above.

  python -m pytest tests/ -v

Expected: full suite green (P1 + P2).
```

---

## Step 2.10 — P2 smoke test script

```
Read AGENT.md before proceeding.

TASK: Write scripts/test_p2_smoke.py — end-to-end proof of P2 without pytest.
This is step 2.10. No new package installs.

─── CREATE scripts/test_p2_smoke.py ───

  """
  P2 smoke test — run: python scripts/test_p2_smoke.py
  Hits real Nominatim + Overpass (network required). Uses dev DB; commits seed data.
  ASCII [OK]/[FAIL] markers for Windows.
  """
  Sections:
    1. Geocoder — geocode("Darjeeling") not None; second call is a cache hit (cache_stats())
    2. Overpass — fetch_pois count >= 50
    3. Seed — run seed logic or subprocess seed_destination.py
    4. DB — destination row place_count >= 50
    5. HTTP — ASGITransport calls to /destinations/search, /places, /readiness
    6. Readiness — tier limited, score in [0.35, 0.45] for unenriched Darjeeling
    7. ★ NEW Rate limit — confirm /destinations/search response carries x-ratelimit-limit: 20
    8. ★ NEW Radius sanity — find_within_radius(dest.lat, dest.lng, radius_km=radius) returns
       a place count roughly consistent with the seeded place_count (catches a silent
       geography/geometry unit regression in production-like conditions, not just unit tests)

─── VALIDATION ───
  python scripts/test_p2_smoke.py

Expected final line:
  ALL P2 SMOKE TESTS PASSED

─── UPDATE docs/context.md ───
  - Last updated: today
  - Next step: P3.1
  - Mark P2 steps ✅ in Progress table
  - Add implemented modules rows (geo, places, destinations services)
  - Update Live endpoints table
  - Add a "Known Limitations" entry: geocoder cache/throttle is per-process; Redis upgrade
    path deferred to P6 (do not let this silently disappear from the record)

─── FAILURE BOUNDARY ───
Network down → smoke script exits non-zero with clear section header — not ambiguous PASS.
```

---

## P2 Complete — Full Verification Checklist (v2)

Run this entire block before starting P3. Every item must pass.

On **Windows PowerShell**, use `Select-String` instead of `grep`.

```bash
# ── Prerequisites ──
docker compose up -d
python scripts/test_p1_smoke.py

# ── Geo gateways (network required) ──
python scripts/test_geocoder.py "Darjeeling"
python scripts/test_overpass.py 27.041 88.263 30

# ── Seed ──
python scripts/seed_destination.py --destination "Darjeeling" --radius 30

# ── OSRM ──
python -c "import asyncio; from src.geo.osrm import get_route; asyncio.run(get_route([(27.04,88.26),(27.03,88.27)]))"

# ── Server ──
uvicorn src.main:app --reload --port 8000

# ── API (replace DESTINATION_ID from seed output) ──
curl -s "http://localhost:8000/api/v1/destinations/search?q=Darjeeling" | python -m json.tool
curl -s "http://localhost:8000/api/v1/destinations/{DESTINATION_ID}/readiness" | python -m json.tool
curl -s "http://localhost:8000/api/v1/places?destination_id={DESTINATION_ID}&page=2&size=10" | python -m json.tool

# ── v2: destination-specific rate limit is active ──
curl -si "http://localhost:8000/api/v1/destinations/search?q=Darjeeling" | Select-String -Pattern "x-ratelimit-limit" -CaseSensitive:$false
# Expected: x-ratelimit-limit: 20

# ── v2: unknown destination on /places is a 404, not an empty page ──
curl -s "http://localhost:8000/api/v1/places?destination_id=00000000-0000-0000-0000-000000000001&page=1" -w "\n%{http_code}"
# Expected: 404

# ── Tests ──
python -m pytest tests/ -v

# ── P2 smoke ──
python scripts/test_p2_smoke.py

# ── Import guards ──
# PowerShell — httpx only in geo/, auth/service, main lifespan:
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "import httpx" | Where-Object { $_.Path -notmatch "(geo\\|auth\\service|main\.py)" }

# ── v2: no lru_cache on async defs anywhere in geo/ (regression guard for the fixed bug) ──
Get-ChildItem -Path src\geo -Recurse -Filter *.py | Select-String "lru_cache"
# Expected: zero results

# ── v2: no lookup-then-create pattern for unique-key upserts — every upsert is on_conflict_do_update ──
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "on_conflict_do_update"
# Expected: at least 2 matches — Place.upsert_from_poi AND Destination.upsert_from_geocoded

echo "P2 COMPLETE — proceed to P3"
```

### P2 ship criteria (v2 — supersedes v1 table)

| Check | Expected |
|-------|----------|
| `GET /destinations/search?q=Darjeeling` | Geocoded result in `data[]` |
| `GET /destinations/{id}/readiness` | `tier=limited`, `score≈0.4`, `place_count>=50` |
| `GET /places?destination_id=...&page=2` | `PaginatedResponse` with `has_next=true` |
| `GET /places?destination_id=<unknown-uuid>` | **404**, not an empty page (v2 locked) |
| Seed script | `Seeded n/n places` idempotent; survives one bad POI (v2 tested) |
| Geocoder failure | Returns `None`, not 500; repeated cache-hit calls do not raise (v2 fixed) |
| OSRM failure | `fallback_used=true` |
| Concurrent destination upsert | No `IntegrityError`, both calls return the same row (v2 fixed) |
| Radius search | Correct at `geography`-cast meter units, verified against a known-distance fixture (v2 locked) |
| `/destinations/search` rate limit | `20/min/IP`, distinct from the `60/min` default (v2 new) |
| pytest | All pass, including the seed-partial-failure and geocoder-cache regression tests (v2 new) |

**Amendment vs blueprint 2.8:** Blueprint says `tier=ready` after seed; with the documented formula, `ready` requires enrichment (P3). P2 acceptance uses `tier=limited`.