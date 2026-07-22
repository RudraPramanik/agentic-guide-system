
# Wandr — P2 Cursor Prompts: Geo Foundation
> Blueprint: [`docs/blueprint_final.md`](../blueprint_final.md) — Phase P2 (4 days · 8 blueprint steps)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> Expanded to **13 prompts** for solidity. New steps marked ★.
> Paste each prompt into Cursor **Agent mode** in order.
> Do NOT advance to the next prompt until the current ✅ validation passes.

## Prerequisites (P1 must be complete)

Before step 2.1, confirm P1 from `docs/context.md`:

- All P1 steps ✅ — models, `BaseRepository`, auth, middleware, pytest harness, `scripts/test_p1_smoke.py`
- Docker Postgres on host port **5433** (`DATABASE_URL=postgresql+asyncpg://wandr:wandr@localhost:5433/wandr`)
- `httpx==0.28.1` and `tenacity==9.1.4` already in `requirements.txt` from P0/P1 — **do not reinstall**
- `shapely==2.1.2` already in `requirements.txt` from step 1.12
- `.env` has a **real** `NOMINATIM_USER_AGENT` with contact email (Nominatim blocks generic agents)
- `python -m pytest tests/ -v` passes (37+ tests)
- `python scripts/test_p1_smoke.py` → `ALL P1 SMOKE TESTS PASSED`

## Prompt conventions (every step)

Each prompt block starts with `Read AGENT.md before proceeding.` Also:

- **Extend, don't replace** P1 code unless the step explicitly says replace.
- **Geo gateway rule:** Nominatim, Overpass, and OSRM HTTP calls happen **only** in `src/geo/`. Services and scripts call `geo/` functions — never construct OverpassQL or hit Nominatim URLs outside `src/geo/`.
- **Layering:** Router → Service → Repository. Routers never import `geo/` or SQLAlchemy directly.
- **Failure boundaries:** external HTTP in `geo/` → retry per Resilience Contracts → named fallback (`None`, `[]`, haversine); never raw 500 from gateway modules. HTTP APIs → typed `WandrError` subclasses.
- **Time:** use `datetime.now(timezone.utc)`, never `datetime.utcnow()`.
- **httpx:** always explicit `httpx.Timeout(connect=..., read=..., write=..., pool=...)` — never bare `timeout=10.0`.
- **Commits:** repositories flush only; services/scripts commit. Match `AuthService` pattern.
- **Windows:** use `Select-String` instead of `grep` where noted in validation.
- **Failure standards:** every prompt has `─── FAILURE BOUNDARY ───` and a `✅ Failure path:` line (see `openspec/specs/step-doc-failure-standards/spec.md`).

---

## P2 architecture (read before implementing)

```
┌──────────────────────────────────────────────────────────────────────┐
│                         P2 dependency graph                          │
└──────────────────────────────────────────────────────────────────────┘

  2.1 geocoder ─────┬────────────────────────────► 2.6 destinations API
  2.2 overpass ─────┤
  2.3 place repo ───┼──► 2.4 seed script ──► 2.7 places API
                    │                              │
                    └──────────────────────────────┴──► 2.8 readiness

  2.5 osrm ── parallel track (standalone gateway; used by P4/P5 later)

  Layer rules:
    scripts/seed_destination.py  →  geo/ + repositories  →  commit
    GET /destinations/search       →  DestinationService   →  repo + geo.geocode
    GET /places                    →  PlaceService         →  PlaceRepository
    geo/*                          →  httpx + tenacity     →  never touches DB
```

**Seed destination (default):** Darjeeling — used in all validation commands below.

---

## Expansion rationale

| Blueprint step | Prompt(s) |
|---|---|
| 2.1 — geocoder + schemas | 2.1 (unchanged) |
| 2.2 — overpass POI scraper | 2.2 (unchanged) |
| 2.3 — places repository | 2.3 (unchanged) |
| 2.4 — seed_destination script | 2.4 (unchanged) |
| 2.5 — OSRM routing | 2.5 (unchanged) |
| 2.6 — destinations domain | **Split → 2.6a** schemas + exceptions · **2.6b** repository + service · **2.6c** router + main.py |
| 2.7 — places API | **Split → 2.7a** schemas + service · **2.7b** router + main.py |
| 2.8 — readiness + endpoint | 2.8 (unchanged) |
| ★ NEW | **2.9** — pytest: geocoder mock, readiness math, API tests |
| ★ NEW | **2.10** — P2 smoke script (seed + endpoint proof) |

**Why split 2.6 / 2.7:** Same lesson as P1 step 1.7 — combined prompts produce DB queries in routers and httpx in services.

**Why add 2.9–2.10:** P2 introduces PostGIS upserts and external HTTP. Unit tests catch readiness math and mocked geocoder paths; smoke script catches real Nominatim/Overpass/geometry I/O.

---

## P2 design decisions (locked for implementation)

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

**P2 note:** Seeded Darjeeling (~144 places, 0 enriched, `search_available=False`) yields **score ≈ 0.4, tier = `limited`**. Tier `ready` requires P3 enrichment/indexing. Step 2.8 validation uses `tier=limited`, not `ready`.

### Destination counters

`Destination.place_count`, `enriched_count`, `indexed_count` are **denormalized**. The seed script sets `place_count` after upserts. P2 readiness reads these counters (not live `COUNT(*)` on every request). P3 scripts update `enriched_count` / `indexed_count`.

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

  Module-level:
    - _HTTP_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0)
    - _rate_lock = asyncio.Lock()
    - _last_request_at: float = 0.0
    - LRU cache: @functools.lru_cache(maxsize=256) on normalized query string

  async def _throttle() -> None:
      """Enforce Nominatim 1 req/sec policy between outbound calls."""

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

  async def geocode(query: str) -> GeocodedPlace | None:
      """
      Public entry point.
      1. Normalize query: strip, collapse whitespace, lower for cache key
      2. Check LRU cache (cache stores GeocodedPlace | None per normalized query)
      3. Call _fetch_nominatim with throttle
      4. Map first result → GeocodedPlace or None if empty
      5. Store in cache, return
      """

  Parsing rules for Nominatim JSON:
    - lat/lng from "lat"/"lon" strings → float
    - osm_place_id = f"{result['osm_type']}/{result['osm_id']}"
    - country from address.country_code (upper) or address.country or "Unknown"
    - name from result["name"] or first segment of display_name

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
- LRU cache is per-process; second identical query must not log an outbound HTTP call.
- Retry only on TimeoutException and ConnectError — never on 404/400.

─── FAILURE BOUNDARY ───
Blueprint row: Nominatim → tenacity 3x → return None.
Must NOT: raise httpx exceptions, return 500, or call Nominatim without User-Agent.

─── VALIDATION ───
Run:
  python scripts/test_geocoder.py "Darjeeling"

Expected (approximate):
  GeocodedPlace(name='Darjeeling', lat=27.041, lng=88.263)

Verify cache (second call, no new HTTP — check logs or mock):
  python -c "
import asyncio
from src.geo import geocoder
async def main():
    r1 = await geocoder.geocode('Darjeeling')
    r2 = await geocoder.geocode('Darjeeling')
    assert r1 is not None and r2 is not None
    info = geocoder.geocode.cache_info()
    assert info.hits >= 1
    print('Cache hits:', info.hits)
    print('PASS')
asyncio.run(main())
"

✅ Failure path: mock _fetch_nominatim to raise httpx.ConnectError — after retries geocode returns None:
  python -c "
import asyncio
from unittest.mock import AsyncMock, patch
import httpx
from src.geo.geocoder import geocode
async def main():
    with patch('src.geo.geocoder._fetch_nominatim', new_callable=AsyncMock, side_effect=httpx.ConnectError('down')):
        geocode.cache_clear()
        assert await geocode('Nowhereville XYZ') is None
    print('PASS — failure returns None')
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
      """Priority-ordered mapping per P2 design decisions table in step2.md."""

  def _element_to_poi(element: dict) -> RawPOI | None:
      """
      - Skip elements with no name tag (unnamed discarded)
      - lat/lng from element lat/lon OR center.lat/center.lon for ways
      - osm_id = f\"{element['type']}/{element['id']}\"
      - category from _category_from_tags(tags)
      - raw_tags = tags dict copy
      """

  @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=16),
         retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)))
  async def _post_overpass(query: str) -> dict:
      """POST to settings.OVERPASS_API_URL with query body. 4xx → log + return {\"elements\": []}."""

  async def fetch_pois(lat: float, lng: float, radius_km: float) -> list[RawPOI]:
      """
      Public entry point.
      1. Build OverpassQL
      2. POST via _post_overpass
      3. Parse elements → RawPOI, skip unnamed
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

TASK: Implement PlaceRepository with PostGIS upsert, radius search, and paginated list.
This is step 2.3. No new package installs.

─── IMPLEMENT src/places/repository.py ───

  import uuid
  from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
  from sqlalchemy import func, select
  from sqlalchemy.dialects.postgresql import insert
  from sqlalchemy.ext.asyncio import AsyncSession

  from src.core.database.base_repository import BaseRepository
  from src.core.pagination import PageParams
  from src.geo.schemas import RawPOI
  from src.places.models import Place

  class PlaceRepository(BaseRepository[Place, uuid.UUID]):

      async def upsert_from_poi(self, poi: RawPOI, destination_id: uuid.UUID) -> Place:
          """
          INSERT ... ON CONFLICT (osm_id) DO UPDATE SET
            name, category, tags, location, destination_id, updated_at
          Location: ST_SetSRID(ST_MakePoint(poi.lng, poi.lat), 4326)  ← lng FIRST
          Flush only — no commit.
          Return the Place instance (query back by osm_id after upsert).
          """

      async def find_within_radius(
          self, lat: float, lng: float, radius_km: float, *, limit: int = 100
      ) -> list[Place]:
          """
          ST_DWithin on location geography cast OR geometry with ::geography
          radius_m = radius_km * 1000
          Exclude soft-deleted (inherit _soft_delete_filter)
          Order by distance optional; limit default 100
          """

      async def list_by_destination(
          self, destination_id: uuid.UUID, params: PageParams
      ) -> tuple[list[Place], int]:
          """Delegate to list_paginated(filters={'destination_id': destination_id}, params=params)."""

      async def count_by_destination(self, destination_id: uuid.UUID) -> int:
          """COUNT non-deleted places for destination — used by seed script."""

─── RULES ───
- ST_MakePoint takes (longitude, latitude) — not (lat, lng).
- upsert_from_poi must be idempotent — running twice updates, does not duplicate.
- Repository never commits — caller commits.
- Use SQLAlchemy 2.0 insert().on_conflict_do_update() — not raw string SQL.

─── FAILURE BOUNDARY ───
DB errors propagate to caller (seed script logs + continues per POI).
Must NOT: commit inside repository, swallow IntegrityError silently without log.

─── VALIDATION ───
Run (inline async test script or pytest-style one-off):
  python -c "
import asyncio, uuid
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
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
        p2 = await repo.upsert_from_poi(poi, dest.id)
        assert p1.id == p2.id, 'upsert must be idempotent'

        nearby = await repo.find_within_radius(27.04, 88.26, 5.divmod(1)[0] or 5)
        assert any(x.id == p1.id for x in await repo.find_within_radius(27.04, 88.26, 5))

        items, total = await repo.list_by_destination(dest.id, PageParams(page=1, size=10))
        assert total >= 1 and items[0].name == 'Test POI'

        shape = to_shape(p1.location)
        assert abs(shape.y - 27.041) < 0.001

        await session.rollback()
        print('PASS — upsert, radius, paginate OK')

asyncio.run(main())
"

✅ Failure path: upsert with invalid destination_id → raises on flush (FK violation) — seed script catches per-POI:
  Document in code comment; verified manually or in step 2.4 test.
```

---

## Step 2.4 — scripts/seed_destination.py

```
Read AGENT.md before proceeding.

TASK: Implement the destination seed CLI — geocode → Overpass → upsert places + Destination row.
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
  from src.destinations.repository import DestinationRepository  # created in 2.6b — see note below

  NOTE: If 2.6b is not done yet, inline minimal Destination upsert via SQLAlchemy here,
  then refactor when DestinationRepository exists. Preferred order: complete 2.6b BEFORE 2.4,
  OR implement a minimal DestinationRepository in this step only.

  RECOMMENDED ORDER AMENDMENT: Do step 2.6b (DestinationRepository) before 2.4,
  OR include a minimal DestinationRepository stub in 2.4 and flesh out in 2.6b.

  Flow:
    1. geocode(destination_name) → GeocodedPlace | exit 1 with message if None
    2. upsert Destination by osm_place_id (create or update lat/lng/display_name)
    3. fetch_pois(lat, lng, radius_km)
    4. For each POI (enumerate):
         try: PlaceRepository.upsert_from_poi
         except Exception: log warning with osm_id, continue
         if (i+1) % 10 == 0: print progress
    5. Update destination.place_count = success_count (enriched_count/indexed_count unchanged)
    6. session.commit()
    7. Print: Seeded {success}/{total} places for {name} (id={dest_id})

─── MINIMAL DestinationRepository (if not yet in 2.6b) ───
  Add to src/destinations/repository.py now (2.6b will extend):
    get_by_osm_place_id(osm_place_id: str) -> Destination | None
    upsert_from_geocoded(geocoded: GeocodedPlace) -> Destination

─── RULES ───
- Single POI failure → log + continue. Never abort full seed for one bad record.
- geocode None → exit code 1, human-readable error (do not commit).
- Overpass [] → commit destination with place_count=0, print warning.
- Script calls geo/ and repositories — not httpx directly.

─── FAILURE BOUNDARY ───
Blueprint: Overpass fail → []. Seed logs warning, destination row still saved with 0 places.
Must NOT: exit 1 on partial POI failures, call Overpass outside geo/.

─── VALIDATION ───
Run:
  python scripts/seed_destination.py --destination "Darjeeling" --radius 30

Expected:
  Seeded {n}/{n} places for Darjeeling   (n >= 50; often ~100–150)
  Final line includes destination UUID

Re-run (idempotent):
  python scripts/seed_destination.py --destination "Darjeeling" --radius 30

Expected: same destination id, no duplicate places (count stable).

✅ Failure path: geocode nonsense → exit 1:
  python scripts/seed_destination.py --destination "XyzzyNonexistentPlace99999"
  Expected: non-zero exit, no commit (or destination not created)
```

---

## Step 2.5 — geo/osrm.py — routing client

```
Read AGENT.md before proceeding.

TASK: Implement the OSRM routing gateway with haversine × 1.4 fallback.
This is step 2.5. No new package installs. Can run in parallel with 2.6–2.8.

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

─── CREATE scripts/test_osrm.py (optional quick check) ───

  python -c "
import asyncio
from src.geo.osrm import get_route
async def main():
    r = await get_route([(27.04, 88.26), (27.03, 88.27)])
    assert r.distance_km > 0 and r.duration_min > 0
    print(f'RouteResult(distance_km={r.distance_km:.2f}, duration_min={r.duration_min:.1f}, fallback={r.fallback_used})')
asyncio.run(main())
"

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

TASK: Implement DestinationRepository and DestinationService with cache-aside search.
This is step 2.6b. No new package installs.

─── IMPLEMENT src/destinations/repository.py ───

  class DestinationRepository(BaseRepository[Destination, uuid.UUID]):

      async def get_by_osm_place_id(self, osm_place_id: str) -> Destination | None: ...

      async def search_by_name(self, query: str, *, limit: int = 10) -> list[Destination]:
          """
          ILIKE on name OR display_name (case-insensitive).
          query sanitized — strip whitespace.
          Order by place_count desc, then name.
          """

      async def upsert_from_geocoded(self, geocoded: GeocodedPlace) -> Destination:
          """
          Lookup by osm_place_id. Create or update lat/lng/name/country/display_name.
          Flush only.
          """

─── IMPLEMENT src/destinations/service.py ───

  class DestinationService:
      def __init__(self, session: AsyncSession): ...

      async def search(self, query: str) -> list[Destination]:
          """
          🏗️ Cache-Aside:
          1. repo.search_by_name(query) — if results: return
          2. geocoded = await geocode(query) — if None: raise DestinationNotFoundError(query=query)
          3. dest = await repo.upsert_from_geocoded(geocoded)
          4. await session.commit(); await session.refresh(dest)
          5. return [dest]
          """
          # Import geocode from src.geo.geocoder only here (service layer), not in router.

      async def get_by_id(self, destination_id: uuid.UUID) -> Destination:
          """get_by_id_or_raise → DestinationNotFoundError if missing."""

─── RULES ───
- search() commits after Nominatim miss path (standalone operation like AuthService.upsert_google_user).
- DB hit path does not call geocode.
- Service never imports httpx — only geo.geocode.

─── FAILURE BOUNDARY ───
geocode None → DestinationNotFoundError 404 at API layer.
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

## Step 2.7a — places/schemas.py + places/service.py

```
Read AGENT.md before proceeding.

TASK: Implement PlaceOut schema and PlaceService.
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

  class PlaceService:
      async def list_by_destination(
          self, destination_id: uuid.UUID, params: PageParams
      ) -> tuple[list[PlaceOut], int]:
          """Verify destination exists (optional: raise NotFoundError). Paginate via repo."""

      async def get_by_id(self, place_id: uuid.UUID) -> PlaceOut:
          """get_by_id_or_raise on Place repo → PlaceOut.from_place"""

─── RULES ───
- PlaceOut lat/lng derived from geometry at serialization time.
- Service uses PlaceRepository only for DB.

─── VALIDATION ───
Requires seeded Darjeeling from step 2.4. Use destination_id from seed output.

  python -c "
import asyncio, uuid
from src.core.database.session import AsyncSessionLocal
from src.core.pagination import PageParams
from src.destinations.repository import DestinationRepository
from src.places.service import PlaceService
async def main():
    async with AsyncSessionLocal() as session:
        dests = await DestinationRepository(session).search_by_name('Darjeeling', limit=1)
        assert dests, 'Run seed_destination.py first'
        items, total = await PlaceService(session).list_by_destination(dests[0].id, PageParams(page=1, size=5))
        assert total >= 1
        assert items[0].lat != 0
        print('PASS', total, 'places')
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
Must NOT: return raw Place ORM model.

─── VALIDATION ───
Use DESTINATION_ID and PAGE from seeded data:

  curl -s "http://localhost:8000/api/v1/places?destination_id={DESTINATION_ID}&page=2&size=10" | python -m json.tool

Expected:
  total >= 50, page=2, pages>=5, has_next=true, items length 10

  curl -s "http://localhost:8000/api/v1/places/{PLACE_ID}" | python -m json.tool

✅ Failure path:
  curl -s "http://localhost:8000/api/v1/places/00000000-0000-0000-0000-000000000001" -w "\n%{http_code}"
  Expected: 404
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
      Pure function — no I/O. Formula in step2.md P2 design decisions.
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

─── ADD to src/destinations/router.py ───

  @router.get("/{destination_id}/readiness")
  async def get_destination_readiness(...) -> ApiResponse[DestinationReadinessOut]: ...

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

## Step 2.9 — P2 pytest coverage ★ NEW

```
Read AGENT.md before proceeding.

TASK: Add pytest tests for geo gateways (mocked), readiness math, and new API routes.
This is step 2.9. No new package installs.

─── CREATE tests/geo/test_geocoder.py ───
  - test_geocode_success (mock _fetch_nominatim)
  - test_geocode_failure_returns_none (mock ConnectError)

─── CREATE tests/geo/test_overpass.py ───
  - test_fetch_pois_deduplicates (mock _post_overpass fixture JSON)
  - test_fetch_pois_failure_returns_empty

─── CREATE tests/geo/test_osrm.py ───
  - test_get_route_fallback_when_osrm_none

─── CREATE tests/destinations/test_readiness.py ───
  - test_compute_readiness_sparse (0 places)
  - test_compute_readiness_limited (144 places, 0 enriched)
  - test_compute_readiness_ready (144 places, 100 enriched, 100 indexed, search_available=True)

─── CREATE tests/destinations/test_destinations_router.py ───
  - test_search_returns_list (mock DestinationService or seed fixture)
  - test_search_not_found_404 (mock geocode None)
  - test_readiness_endpoint (seed destination in db_session)

─── CREATE tests/places/test_places_router.py ───
  - test_list_places_paginated (insert destination + places in db_session)
  - test_get_place_404

─── RULES ───
- Mock external HTTP in unit tests — do not hit Nominatim/Overpass/OSRM in CI.
- Use existing db_session fixture from tests/conftest.py.
- Tests that need places: insert Destination + Place rows with from_shape(Point(lng, lat)).

─── VALIDATION ───
  python -m pytest tests/geo tests/destinations tests/places -v

Expected: all new tests pass.

  python -m pytest tests/ -v

Expected: full suite green (P1 + P2).
```

---

## Step 2.10 — P2 smoke test script ★ NEW

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
    1. Geocoder — geocode("Darjeeling") not None
    2. Overpass — fetch_pois count >= 50
    3. Seed — run seed logic or subprocess seed_destination.py
    4. DB — destination row place_count >= 50
    5. HTTP — ASGITransport calls to /destinations/search, /places, /readiness
    6. Readiness — tier limited, score in [0.35, 0.45] for unenriched Darjeeling

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

─── FAILURE BOUNDARY ───
Network down → smoke script exits non-zero with clear section header — not ambiguous PASS.
```

---

## Recommended implementation order (amended)

The expansion splits domains, but **seed script needs DestinationRepository**. Use this order:

```
2.1 → 2.2 → 2.3 → 2.6a → 2.6b → 2.4 → 2.5 → 2.6c → 2.7a → 2.7b → 2.8 → 2.9 → 2.10
```

Steps **2.6a/b before 2.4** avoids a throwaway Destination upsert in the seed script.

---

## P2 Complete — Full Verification Checklist

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

# ── Tests ──
python -m pytest tests/ -v

# ── P2 smoke ──
python scripts/test_p2_smoke.py

# ── Import guards ──
# PowerShell — httpx only in geo/, auth/service, main lifespan:
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "import httpx" | Where-Object { $_.Path -notmatch "(geo\\|auth\\service|main\.py)" }

echo "P2 COMPLETE — proceed to P3"
```

### P2 ship criteria (from blueprint, amended for readiness math)

| Check | Expected |
|-------|----------|
| `GET /destinations/search?q=Darjeeling` | Geocoded result in `data[]` |
| `GET /destinations/{id}/readiness` | `tier=limited`, `score≈0.4`, `place_count>=50` |
| `GET /places?destination_id=...&page=2` | `PaginatedResponse` with `has_next=true` |
| Seed script | `Seeded n/n places` idempotent |
| Geocoder failure | Returns `None`, not 500 |
| OSRM failure | `fallback_used=true` |
| pytest | All pass |

**Amendment vs blueprint 2.8:** Blueprint says `tier=ready` after seed; with the documented formula, `ready` requires enrichment (P3). P2 acceptance uses `tier=limited`.
