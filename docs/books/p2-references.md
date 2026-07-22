# P2 References — Books, Docs & Deep Links

> Companion to [`docs/app/p2guide.md`](../app/p2guide.md).  
> Prefer official docs + one strong book per topic over random blog spam.

---

## 1. System design & backend patterns

| Resource | Why it maps to P2 |
|----------|-------------------|
| [Designing Data-Intensive Applications](https://dataintensive.net/) — Martin Kleppmann | Cache-aside, retries vs idempotency, denormalization trade-offs (`place_count`) |
| [Patterns of Enterprise Application Architecture](https://martinfowler.com/books/eaa.html) — Martin Fowler | Gateway, Repository, Service Layer, Unit of Work (our Router→Service→Repo + session-per-request) |
| [Microsoft Cloud Design Patterns — Gateway Aggregation / Gateway Routing](https://learn.microsoft.com/en-us/azure/architecture/patterns/) | Mental model for `src/geo/*` as edge adapters |
| [Cache-Aside pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) | Destination search: DB first, Nominatim on miss |

---

## 2. Resilience, timeouts & retries

| Resource | Why it maps to P2 |
|----------|-------------------|
| [Release It! (2nd ed.)](https://pragprog.com/titles/mnee2/release-it-second-edition/) — Michael Nygard | Timeouts, bulkheads, “named fallbacks”; never let externals become opaque 500s |
| [tenacity documentation](https://tenacity.readthedocs.io/) | Exact library Wandr uses for geo + LLM retries |
| [httpx Timeouts](https://www.python-httpx.org/advanced/timeouts/) | Explicit `connect` / `read` / `write` / `pool` — matches AGENT.md |
| [AWS — Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) | Why exponential backoff; why not retry 4xx |

---

## 3. Async Python

| Resource | Why it maps to P2 |
|----------|-------------------|
| [asyncio — Locks](https://docs.python.org/3/library/asyncio-sync.html) | Geocoder rate lock + cache lock |
| [functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache) | Understand why it must **not** decorate `async def` |
| [SQLAlchemy 2.0 asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) | AsyncSession, flush vs commit |

---

## 4. PostGIS & spatial

| Resource | Why it maps to P2 |
|----------|-------------------|
| [PostGIS — Geography](https://postgis.net/workshops/postgis-intro/geography.html) | Why radius queries use `geography` + meters |
| [PostGIS — ST_DWithin](https://postgis.net/docs/ST_DWithin.html) | `find_within_radius` |
| [PostGIS — ST_MakePoint](https://postgis.net/docs/ST_MakePoint.html) | `(x,y)` = `(lng, lat)` |
| [GeoAlchemy 2 docs](https://geoalchemy-2.readthedocs.io/) | SQLAlchemy + PostGIS types Wandr uses |
| [Shapely manual](https://shapely.readthedocs.io/) | Building points for seeds/tests (`from_shape` / `to_shape`) |

**Book (optional deep dive):** *PostGIS in Action* (Obe & Hsu) — chapters on geography vs geometry and spatial indexes.

---

## 5. OpenStreetMap stack (Nominatim, Overpass, OSRM)

| Resource | Why it maps to P2 |
|----------|-------------------|
| [Nominatim API / Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) | User-Agent, 1 req/sec — non-negotiable |
| [Nominatim Search API](https://nominatim.org/release-docs/latest/api/Search/) | Query params Wandr geocoder uses |
| [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) | POI scrape language + etiquette |
| [Overpass QL language guide](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) | `around:`, tourism filters |
| [OSRM HTTP API](http://project-osrm.org/docs/v5.24.0/api/#general-options) | Route service Wandr wraps |
| [OSRM demo server note](https://github.com/Project-OSRM/osrm-backend/wiki/Api-usage-policy) | Why public OSRM needs fallback |

---

## 6. Postgres upserts & concurrency

| Resource | Why it maps to P2 |
|----------|-------------------|
| [PostgreSQL INSERT … ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT) | Atomic upsert for `osm_id` / `osm_place_id` |
| [SQLAlchemy PostgreSQL INSERT…ON CONFLICT](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert) | `insert().on_conflict_do_update().returning()` |

---

## 7. FastAPI / API design

| Resource | Why it maps to P2 |
|----------|-------------------|
| [FastAPI — Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) | Router modules for destinations/places |
| [FastAPI — Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) | `get_db`, `PageParams` |
| [RFC 6585 — Additional HTTP Status Codes](https://datatracker.ietf.org/doc/html/rfc6585) | 429 + `Retry-After` (rate limit on search) |

---

## 8. Interview prep (broader)

| Resource | Focus |
|----------|--------|
| [System Design Interview — Alex Xu](https://bytebytego.com/) | Rate limiting, caching, geo services at a high level |
| [Staff Engineer — Will Larson](https://staffeng.com/book) | Documenting known limitations (per-process geocode cache → Redis) |
| Wandr internal Q&A | [`docs/app/p2guide.md` §4](../app/p2guide.md) |

---

## Suggested study order (1–2 evenings before coding P2)

1. Nominatim usage policy + httpx timeouts  
2. PostGIS geography workshop (one chapter)  
3. Postgres `ON CONFLICT` + SQLAlchemy upsert example  
4. Kleppmann / Fowler skim: cache-aside + gateway  
5. Re-read Wandr [`step2.md` Fix Log](../steps/step2.md) and resilience table in [`blueprint_final.md`](../blueprint_final.md)
