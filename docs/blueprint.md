# Wandr — Backend Blueprint v3
> Production-grade AI travel planner(map visualizatin based in frontend). Modular monolith. Thin vertical slices. Every step ends with a runnable proof.

---

## Principles

| # | Principle |
|---|-----------|
| 1 | **Packages at point of use** — nothing installed until the step that needs it |
| 2 | **LLD pattern named per step** — every design decision is explicit |
| 3 | **Failure boundary per step** — every external call has a fallback |
| 4 | **Production layer abstracted from step 1** — same code runs locally and in prod via env vars |
| 5 | **Lightest viable package** — no heavy dependencies without justification |
| 6 | **Travel intelligence is a first-class layer** — not buried in LangGraph nodes |
| 7 | **Evaluation from day one** — every generated trip is stored for quality analysis |

---

## Project Structure

```
wandr-backend/
├── alembic/                        # migrations only, no logic
├── alembic.ini
├── docker-compose.yml              # local dev infra only (never used in prod)
├── requirements.txt                # append-only, packages added at point of use
├── .env.example
├── scripts/                        # one-off CLI tools, never imported by app
│   ├── seed_destination.py
│   ├── enrich_places.py
│   ├── index_places.py
│   └── test_agent.py
├── tests/
│   ├── conftest.py
│   ├── auth/
│   ├── planner/
│   ├── geo/
│   └── trips/
└── src/
    ├── main.py                     # app factory, lifespan, router registration
    ├── config.py                   # Pydantic Settings — all env vars, one place
    │
    ├── core/                       # cross-cutting infrastructure, no business logic
    │   ├── database/
    │   │   ├── base.py             # DeclarativeBase, UUIDMixin, TimestampMixin, SoftDeleteMixin
    │   │   ├── session.py          # async engine, connection pool, get_db() dependency
    │   │   └── base_repository.py  # Generic[M, ID] — CRUD + paginate implemented once
    │   ├── security/
    │   │   ├── jwt.py              # create_access_token, verify_token
    │   │   └── permissions.py      # require_auth, optional_auth FastAPI dependencies
    │   ├── middleware/
    │   │   ├── logging.py          # request_id, latency, structlog context binding
    │   │   └── rate_limit.py       # in-memory dev / Redis prod, same interface
    │   ├── observability/
    │   │   ├── logging.py          # structlog config — ConsoleRenderer dev, JSONRenderer prod
    │   │   └── tracing.py          # Langfuse lazy init, NoOpTracer if keys missing
    │   ├── pagination.py           # PageParams, PaginatedResponse[T], paginate()
    │   ├── responses.py            # ApiResponse[T], ErrorResponse
    │   └── exceptions.py           # WandrError hierarchy → NotFoundError, UnauthorizedError, etc.
    │
    ├── auth/                       # domain module
    │   ├── router.py               # /api/v1/auth/...
    │   ├── schemas.py
    │   ├── models.py               # User
    │   ├── repository.py           # extends BaseRepository
    │   ├── service.py              # google_oauth_flow, issue_jwt, anonymous_session
    │   ├── dependencies.py         # get_current_user, get_optional_user
    │   └── exceptions.py
    │
    ├── destinations/               # domain module
    │   ├── router.py               # /api/v1/destinations/search
    │   ├── schemas.py
    │   ├── models.py               # Destination (cached geocode result)
    │   ├── repository.py
    │   └── service.py              # DB-first lookup, Nominatim fallback
    │
    ├── places/                     # domain module
    │   ├── router.py               # /api/v1/places/
    │   ├── schemas.py
    │   ├── models.py               # Place with PostGIS POINT column
    │   ├── repository.py           # upsert_from_poi, find_within_radius, list_paginated
    │   └── service.py              # enrich_place (LLM summary + tags)
    │
    ├── trips/                      # domain module
    │   ├── router.py               # /api/v1/trips/ CRUD + /geojson
    │   ├── schemas.py
    │   ├── models.py               # Trip, TripPlace
    │   ├── repository.py
    │   ├── service.py              # save_from_state, build_geojson, ownership check
    │   └── exceptions.py
    │
    ├── planner/                    # domain module — AI agent orchestration
    │   ├── router.py               # /api/v1/planner/generate (streaming SSE)
    │   ├── schemas.py              # PlanRequest, PlanResult, ItineraryDay
    │   ├── service.py              # cache-aside wrapper around graph.invoke()
    │   └── graph/
    │       ├── state.py            # TravelState TypedDict — single object through all nodes
    │       ├── builder.py          # build_graph() → CompiledGraph singleton
    │       └── nodes/
    │           ├── preference.py   # parse raw input → structured prefs (Groq JSON mode)
    │           ├── poi_retrieval.py # Qdrant semantic search + PostGIS fallback
    │           ├── ranking.py      # pure Python scorer — no LLM
    │           ├── route_planner.py # calls travel_engine — no logic here
    │           ├── itinerary.py    # LLM narrative only — structure comes from travel_engine
    │           └── validation.py   # paranoid output checks before leaving agent
    │
    ├── travel_engine/              # ★ travel intelligence layer — destination-agnostic rules
    │   ├── travel_rules.py         # constants: max places/day, min travel buffer, category weights
    │   ├── place_selector.py       # which places? why? what gets excluded?
    │   ├── day_allocator.py        # how many days? how many places per day?
    │   ├── route_optimizer.py      # what order? how much travel time between stops?
    │   └── trip_validator.py       # is this a realistic, good trip?
    │
    ├── evaluation/                 # ★ trip quality data — stored from day one
    │   ├── models.py               # TripEvaluation — stores every generation event
    │   ├── repository.py
    │   ├── service.py              # record_generation(), get_quality_report()
    │   └── schemas.py              # EvalRecord, QualityReport
    │
    ├── geo/                        # infrastructure — external geo service wrappers
    │   ├── geocoder.py             # Nominatim async client, LRU cache, rate limit
    │   ├── overpass.py             # POI scraper — used by seed scripts only
    │   ├── osrm.py                 # routing + polylines, straight-line fallback
    │   └── schemas.py              # GeocodedPlace, RawPOI, RouteResult
    │
    └── search/                     # infrastructure — Qdrant wrapper
        ├── client.py               # get_qdrant_client() singleton, ensure_collection()
        ├── embeddings.py           # embed_text(), embed_batch() — model abstracted
        └── places_index.py         # upsert_place(), search_places()
```

---

## Environment Variables

```bash
# Core
ENVIRONMENT=development          # development | production
DEBUG=true
SECRET_KEY=                      # long random string, never hardcoded

# Database
DATABASE_URL=                    # local: postgresql+asyncpg://...  prod: Neon/Supabase URL

# Vector search
QDRANT_URL=http://localhost:6333 # prod: https://xxx.qdrant.io
QDRANT_API_KEY=                  # empty for local, required for Qdrant Cloud

# Cache (optional — features degrade gracefully if missing)
REDIS_URL=                       # empty in dev (in-memory fallback), prod: Upstash URL

# LLM
GROQ_API_KEY=                    # Groq free tier for Llama 3

# Observability
LANGFUSE_PUBLIC_KEY=             # optional — NoOpTracer used if missing
LANGFUSE_SECRET_KEY=

# Geo
NOMINATIM_USER_AGENT=wandr-dev-yourname@email.com   # required by OSM policy

# OSRM
OSRM_BASE_URL=https://router.project-osrm.org       # prod: self-hosted or Valhalla
```

**Production mapping:**
| Dev | Prod |
|-----|------|
| Local Postgres (Docker) | Neon / Supabase / Railway |
| Local Qdrant (Docker) | Qdrant Cloud free tier |
| No Redis | Upstash free tier |
| Console logs | Logtail / Datadog (JSONRenderer, zero config change) |
| Public OSRM | Self-hosted OSRM or Valhalla |

---

## travel_engine — Design

The travel intelligence layer. All destination-agnostic planning rules live here.  
LangGraph nodes call this layer — they do not contain planning logic themselves.

### travel_rules.py
Constants and configuration that govern all planning decisions.
```python
MAX_PLACES_PER_DAY = 6
MIN_TRAVEL_BUFFER_MIN = 30        # minimum gap between stops for transit
CATEGORY_WEIGHTS = {
    "photography": 1.4,
    "offbeat": 1.3,
    "viewpoint": 1.2,
    "trek": 1.1,
    "cultural": 1.0,
    "family": 0.9,
}
MORNING_CATEGORIES = ["viewpoint", "photography"]   # Tiger Hill = sunrise only
AVOID_SAME_DAY = [("monastery", "monastery")]        # don't stack same category
```

### place_selector.py
Answers: *which places? why these? what gets excluded?*
- Filter candidates by interest tags and budget
- Apply exclusion rules (e.g. a sunrise viewpoint cannot be Day 2 Stop 4 at 3pm)
- Score with category weights from travel_rules
- Remove places that conflict with each other on the same day

### day_allocator.py
Answers: *how many places per day? how long at each?*
- Calculate realistic visit duration per category (monastery = 45min, viewpoint = 20min)
- Cap day load by total time budget (8hr active day)
- Distribute places across days by geographic cluster and time load

### route_optimizer.py
Answers: *what order? how much travel time?*
- Nearest-neighbour ordering within each day's cluster
- OSRM travel times between consecutive stops
- Identify if a day's total travel exceeds threshold → reorder or drop a stop
- Output: ordered stops per day with realistic travel_time_min between each

### trip_validator.py
Answers: *is this a good, realistic trip?*
- Total daily travel time < 3 hours
- No place repeated across days
- Sunrise places scheduled in morning slots
- At least one "anchor" attraction per day
- Geographic coherence: day's places are clustered, not scattered

---

## evaluation — Design

Every generated trip is recorded. Not for users — for you, to improve quality over time.

### What gets stored (TripEvaluation)
```python
class TripEvaluation:
    id: UUID
    trip_id: UUID | None          # null if anonymous, linked if saved
    destination_id: UUID
    
    # Input
    raw_input: str
    parsed_preferences: dict      # what the preference node extracted
    
    # Pipeline
    candidates_retrieved: int     # how many POIs came back from Qdrant
    candidates_after_ranking: int # after scoring
    
    # Output
    final_route: dict             # the actual itinerary JSON
    places_per_day: list[int]     # [5, 6, 4] — distribution
    total_distance_km: float
    
    # Performance
    generation_time_ms: int
    token_usage: dict             # {preference_node: 120, itinerary_node: 890}
    llm_model: str
    
    # Quality signals (filled later)
    validation_passed: bool
    validation_warnings: list[str]
    user_saved: bool              # did the user save this trip?
    user_edited: bool             # did they modify it? (strong quality signal)
    
    created_at: datetime
```

### Why this matters
- `user_saved=True` + `validation_passed=True` = good trip signal
- `user_edited=True` = something was wrong — which places got removed?
- High `generation_time_ms` = which node is slow?
- Low `candidates_retrieved` = Qdrant data gap for that destination
- `validation_warnings` patterns = systematic planner bugs

You will look at this data after 50 generated trips and know exactly what to fix.

---

## Phase Blueprint

### Legend
- 📦 Package installed at this step
- 🏗️ LLD pattern
- 🚨 Failure boundary
- ☁️ Production consideration

---

### P0 — Scaffold, Config & Core Conventions
**2 days · 9 steps**

#### 0.1 Repo + full directory skeleton
- Create entire folder tree. Empty `__init__.py` in each folder.
- Includes `travel_engine/` and `evaluation/` from the start.
- 🏗️ **Modular Monolith** — each domain folder self-contained
- 🚨 Import failure at startup → clear module path in error, not silent 500
- ✅ `find src/ -type d | sort` → full tree, zero import errors

#### 0.2 src/config.py — Pydantic Settings
- 📦 `pydantic-settings`
- `class Settings(BaseSettings)` — all env vars grouped by concern
- `@lru_cache def get_settings()` — loaded once per process
- 🏗️ **Singleton** — no re-parsing on every request
- ☁️ Dev reads `.env` file. Prod reads real env vars (Railway/Render/ECS). Zero code change.
- 🚨 Missing required key at startup → `ValidationError` with field name, app refuses to start
- ✅ `python -c "from src.config import get_settings; print(get_settings().ENVIRONMENT)"` → `"development"`

#### 0.3 docker-compose.yml
- `postgis/postgis:16-3.4` with healthcheck + named volume
- `qdrant/qdrant:latest` port 6333 + named volume
- No Redis — `REDIS_URL` is `None` in dev, feature-flagged off
- ☁️ Prod has no docker-compose. All services are hosted APIs injected via env vars.
- 🚨 Postgres unhealthy → app lifespan logs "DB unreachable" and exits. No zombie process.
- ✅ `docker compose up -d` → both containers healthy

#### 0.4 core/observability/logging.py — structlog
- 📦 `structlog`
- Dev: `ConsoleRenderer`. Prod: `JSONRenderer`.
- `configure_logging()` called once in app lifespan
- 🏗️ **Context Propagation** — `bind_contextvars()` flows request_id through all log lines
- ☁️ JSONRenderer output pipes into Logtail/Datadog/CloudWatch with zero config change
- ✅ `structlog.get_logger().info("boot", env="dev")` → formatted log line

#### 0.5 core/observability/tracing.py — Langfuse
- 📦 `langfuse`
- `get_tracer() → Langfuse | NoOpTracer` — NoOpTracer has identical interface
- 🏗️ **Null Object Pattern** — callers never write `if tracer:` checks
- 🚨 Langfuse flush errors caught and logged as warnings — never propagate to user request
- ✅ `get_tracer().trace("test")` → no crash with or without keys

#### 0.6 core/pagination.py
- `PageParams`: page=1, size=20, max=100, computed offset
- `PaginatedResponse[T](BaseModel, Generic[T])`: items, total, page, size, pages, has_next, has_prev
- `paginate(result, total, params)` helper
- 🏗️ **Generic Repository** — every list endpoint is typed and consistent
- ✅ `PaginatedResponse(items=[], total=55, page=1, size=20, pages=3)` → `has_next=True`

#### 0.7 core/responses.py
- `ApiResponse[T]`: success, data, message
- `ErrorResponse`: success=False, code, message, details
- 🏗️ **Response Envelope** — frontend has one error handler, not many
- ✅ Both models serialise to clean JSON

#### 0.8 core/exceptions.py — WandrError hierarchy
- `WandrError(code, message, status_code, details)` base
- Subclasses: `NotFoundError(404)`, `UnauthorizedError(401)`, `ForbiddenError(403)`, `ExternalServiceError(502)`
- 🏗️ **Exception Hierarchy** — single global handler catches all domain errors
- 🚨 Unhandled exceptions → full traceback logged server-side, generic `ErrorResponse` to client. No stack trace leakage.
- ✅ `raise NotFoundError(code="trip_not_found")` → caught → 404 `ErrorResponse`

#### 0.9 src/main.py — app factory + lifespan + /health
- 📦 `fastapi` `uvicorn[standard]`
- `create_app() → FastAPI` factory — enables test client injection
- Lifespan: startup → configure_logging, DB ping, Qdrant ping. Shutdown → close pool.
- `GET /api/v1/health` → `{"status":"ok","env":"development","version":"1.0.0"}`
- 🏗️ **App Factory** — decouples creation from execution
- ☁️ `/health` used as liveness probe by Railway/Render/ECS. Returns 503 if DB unreachable.
- 🚨 DB ping fails at startup → log critical + `exit(1)`. Visible crash > silent broken state.
- ✅ `uvicorn src.main:app` → `GET /api/v1/health` → 200 + structured log line

---

### P1 — Database Foundation + Auth
**3 days · 8 steps**

#### 1.1 core/database/base.py — declarative base + mixins
- 📦 `sqlalchemy[asyncio]` `asyncpg`
- `Base = DeclarativeBase()`
- `UUIDMixin`: `id = mapped_column(UUID, default=uuid4, primary_key=True)`
- `TimestampMixin`: created_at server_default, updated_at onupdate
- `SoftDeleteMixin`: deleted_at nullable — repos filter `deleted_at IS NULL` by default
- 🏗️ **Mixin Inheritance** — horizontal reuse, each mixin does one thing
- ✅ `from src.core.database.base import Base, TimestampMixin` → no error

#### 1.2 core/database/session.py — async engine + pool
- `create_async_engine(DATABASE_URL, pool_size=10, max_overflow=20, pool_pre_ping=True)`
- `async_sessionmaker(expire_on_commit=False)`
- `async def get_db() → AsyncSession` — yields, closes in finally
- 🏗️ **Unit of Work** — one session per request, shared transaction context
- ☁️ `pool_pre_ping=True` recycles stale connections on hosted Postgres (Neon/Supabase idle drops)
- 🚨 Connection timeout → `ExternalServiceError` 502, not 500
- ✅ `scripts/test_db_conn.py` → "PostgreSQL 16.x connected, pool ok"

#### 1.3 Alembic init + migration 001: PostGIS
- 📦 `alembic` `geoalchemy2`
- Configure `env.py` for async engine + Base metadata import
- Migration 001: `CREATE EXTENSION IF NOT EXISTS postgis`
- ☁️ Run `alembic upgrade head` as deploy step — never inside app startup
- 🚨 Failed migration auto-rolls back. Bad migration never takes down running app.
- ✅ `alembic upgrade head` → "Running upgrade → 001_enable_postgis"

#### 1.4 All core models — migration 002
- `auth/models.py` — User: id, email, name, avatar_url, google_id, is_active
- `places/models.py` — Place: id, osm_id(unique), name, category, tags(JSONB), summary, location(Geometry POINT 4326), destination_id
- `trips/models.py` — Trip: id, user_id(nullable), session_id, destination_id, days, preferences(JSONB), status(enum)
- `trips/models.py` — TripPlace: id, trip_id, place_id, day_number, order_in_day, travel_time_min, polyline
- `evaluation/models.py` — TripEvaluation (full schema above)
- Indexes: `Place.osm_id`, `Place.destination_id`, `Trip.session_id`, `Trip.user_id`
- 🏗️ **Domain Model** — each model lives in its domain module
- 🚨 Missing index on high-query columns = silent prod degradation. Add now.
- ✅ `alembic upgrade head` → all tables + indexes visible in `psql \dt \di`

#### 1.5 core/database/base_repository.py — generic repo base
- `class BaseRepository[M, ID]`
- Methods: `get_by_id()`, `create()`, `update()`, `soft_delete()`, `list_paginated(filters, params) → tuple[list[M], int]`
- `list_paginated` auto-applies `deleted_at IS NULL` from SoftDeleteMixin
- 🏗️ **Generic Repository** — domain repos extend this, get CRUD free
- 🏗️ **Specification Pattern** — `filters: dict` not raw SQL in callers
- ✅ `from src.core.database.base_repository import BaseRepository` → no error

#### 1.6 core/security/jwt.py + permissions.py
- 📦 `python-jose[cryptography]`
- `create_access_token(user_id, email) → str` — HS256, 7 day expiry
- `verify_token(token) → TokenPayload | None` — returns None on invalid, never raises
- `require_auth` → raises UnauthorizedError. `optional_auth` → returns user or None.
- ☁️ SECRET_KEY in prod = long random string from env, never hardcoded. Rotate by changing env var.
- 🚨 Expired token → 401. Malformed token → 401. Never 422 or 500.
- ✅ `verify_token(create_access_token(...))` → payload. `verify_token("bad")` → None

#### 1.7 auth/ — repository, service, router
- 📦 `httpx` (used for Google OAuth + all external HTTP going forward)
- `UserRepository(BaseRepository[User, UUID])`: `get_by_email()`, `get_by_google_id()`
- `AuthService`: `upsert_google_user()`, anonymous session UUID in httpOnly cookie
- `GET /api/v1/auth/google` → `GET /api/v1/auth/callback` → `GET /api/v1/auth/me` → `POST /api/v1/auth/logout`
- 🏗️ **Service Layer** — router calls service only, service calls repo, router knows nothing about DB
- 🚨 Google OAuth timeout → `ExternalServiceError` 502. Callback failure → redirect to `/auth/error`, never a 500 page.
- ✅ `GET /api/v1/auth/me` (no token) → `{"data":{"is_guest":true,"session_id":"uuid..."}}`

#### 1.8 core/middleware/logging.py
- Generate `X-Request-ID` per request, bind to structlog context
- Log `request.start` and `request.end` with latency_ms
- Return `X-Request-ID` in response headers
- 🏗️ **Chain of Responsibility** — middleware chain: request_id → logging → auth → rate_limit → handler
- ☁️ `X-Request-ID` in response lets support correlate user bug reports to specific log lines
- ✅ `GET /api/v1/health` → response header `X-Request-ID` present + `request.end` log with latency_ms

---

### P2 — Geo Foundation
**4 days · 7 steps**

#### 2.1 geo/geocoder.py — Nominatim client
- `geo/schemas.py`: `GeocodedPlace(name, lat, lng, osm_place_id, country, display_name)`
- `geocode(query) → GeocodedPlace | None` — async httpx, 1 req/sec rate limit, User-Agent from config
- LRU cache on query string — same query never hits Nominatim twice in same process
- 🏗️ **Gateway Pattern** — all geocoding through one module, swap provider by changing one file
- ☁️ MVP: Nominatim free. Scale: add Redis cache layer here before calling Nominatim. Zero caller changes.
- 🚨 Nominatim timeout → log warning, return None. Caller raises DestinationNotFound (404). Nominatim is not critical path — app works if destinations pre-seeded.
- ✅ `scripts/test_geocoder.py "Darjeeling"` → `GeocodedPlace(lat=27.041, lng=88.263)`

#### 2.2 geo/overpass.py — POI scraper
- `RawPOI(osm_id, name, lat, lng, category, raw_tags: dict)`
- OverpassQL: `tourism=attraction|viewpoint|museum|monastery` + `leisure=park` + `highway=trailhead` within radius
- Filter: unnamed nodes discarded. Deduplicate by osm_id. Store all raw OSM tags.
- 🏗️ **Gateway Pattern** — single Overpass entry point
- 🚨 Overpass only called by seed scripts (offline). Never in request path. Script catches timeout, continues with partial results. Zero live app impact.
- ✅ `scripts/test_overpass.py 27.041 88.263 30` → "Fetched 144 POIs"

#### 2.3 places/repository.py — upsert + radius + paginated
- `PlaceRepository(BaseRepository[Place, UUID])`
- `upsert_from_poi(poi, destination_id)` — `ON CONFLICT(osm_id) DO UPDATE`
- `find_within_radius(lat, lng, km)` — `ST_DWithin` on location column
- `list_by_destination(destination_id, params)` — inherits paginate from base
- 🚨 PostGIS extension missing → clear error at startup ping, not cryptic SQL error mid-request
- ✅ Insert 1 place, radius query finds it, paginated list returns it

#### 2.4 scripts/seed_destination.py
- Args: `--destination "Darjeeling" --radius 30`
- Geocode → Overpass → upsert places + Destination row
- Re-runnable (upsert). Progress per 10. Summary at end.
- 🚨 Single POI upsert fail → log + continue. Full seed never aborted for one bad record.
- ✅ `python scripts/seed_destination.py --destination "Darjeeling"` → "Seeded 144/144 places"

#### 2.5 geo/osrm.py — routing client
- `RouteResult(distance_km, duration_min, encoded_polyline)`
- `get_route(waypoints: list[tuple[float,float]]) → RouteResult`
- ☁️ Public OSRM demo for MVP. Prod: self-hosted OSRM or Valhalla. Swap `OSRM_BASE_URL` in config only.
- 🚨 OSRM timeout → log warning, return straight-line `RouteResult`. Itinerary still valid. Never fails a user request.
- ✅ `get_route([(27.04,88.26),(27.03,88.27)])` → `RouteResult(distance_km=1.8, polyline="...")`

#### 2.6 destinations/ — repository, service, router
- `DestinationRepository(BaseRepository[Destination, UUID])`: `get_by_osm_place_id()`, `search_by_name()`
- `DestinationService.search(query)` — DB first, Nominatim on miss, save result
- `GET /api/v1/destinations/search?q=`
- 🏗️ **Cache-Aside** — check DB → miss → fetch external → write DB → return
- ✅ Two searches for "Darjeeling" → second has no Nominatim log line

#### 2.7 places/router.py — paginated list + single get
- `PlaceService`: `list_by_destination()`, `get_by_id()`
- `GET /api/v1/places?destination_id=&page=1&size=20` → `PaginatedResponse[PlaceOut]`
- `GET /api/v1/places/{id}` → `ApiResponse[PlaceOut]` or `NotFoundError` 404
- 🚨 Invalid UUID in path → 422 from Pydantic. Missing destination_id → 422. Both use `ErrorResponse` shape.
- ✅ `GET /api/v1/places?destination_id=...&page=2&size=10` → `{"total":144,"page":2,"pages":15,"has_next":true}`

---

### P3 — Place Knowledge Layer
**3 days · 5 steps**

#### 3.1 search/client.py — Qdrant init
- 📦 `qdrant-client`
- `get_qdrant_client()` cached singleton
- `ensure_places_collection()` idempotent — vector size=384, cosine distance
- Called in app lifespan startup
- ☁️ Local: `QDRANT_URL=http://localhost:6333`, no key. Prod: `QDRANT_URL=https://xxx.qdrant.io` + `QDRANT_API_KEY`. Zero code change.
- 🚨 Qdrant unreachable at startup → log warning, set `search_available=False` flag. Planner falls back to PostGIS. App still serves requests.
- ✅ App startup → "Qdrant collection 'places' ready (0 vectors)" in logs

#### 3.2 search/embeddings.py — embed_text abstraction
- 📦 `sentence-transformers` — runs locally, no API key, free forever. Model: `all-MiniLM-L6-v2` (384d, 80MB)
- `embed_text(text: str) → list[float]` — model loaded once at module level
- `embed_batch(texts: list[str]) → list[list[float]]`
- 🏗️ **Strategy Pattern** — swap to OpenAI/Groq embeddings by changing one function body, not all callers
- ☁️ sentence-transformers runs in prod too (model cached after first download). No API cost.
- ✅ `embed_text("sunrise photography")` → list of 384 floats

#### 3.3 places/service.py — enrich_place()
- 📦 `groq`
- `enrich_place(place) → EnrichedPlace(summary, tags)`
- Groq JSON mode: name + raw OSM tags → `{summary: str, tags: list[str]}`
- Tags from controlled vocab: `offbeat, photography, viewpoint, trek, monastery, cultural, family, nature, adventure`
- Skip if `place.summary` already set — re-runnable
- 🚨 Groq timeout → log + skip place, continue batch. Rate limit (429) → exponential backoff 3 retries.
- ✅ `enrich_place(tiger_hill)` → `{"summary":"Tiger Hill is...","tags":["photography","viewpoint","sunrise"]}`

#### 3.4 search/places_index.py — upsert + semantic search
- `upsert_place(place)` — embeds summary+tags, stores with payload: `{place_id, name, destination_id, lat, lng, tags, category}`
- `search_places(query, destination_id, top_k) → list[PlaceSearchResult]`
- `PlaceSearchResult`: place_id, name, score, lat, lng, tags
- 🏗️ **Repository Pattern** — Qdrant treated as another persistence layer
- 🚨 Qdrant search failure → catch, log warning, return empty list. Planner uses PostGIS fallback. Degraded but functional.
- ✅ `search_places("photography sunrise", darjeeling_id, 10)` → Tiger Hill first

#### 3.5 scripts/enrich_places.py + scripts/index_places.py
- `enrich_places.py --destination Darjeeling` — batches of 10, progress printed, re-runnable
- `index_places.py --destination Darjeeling` — embeds all enriched places, upserts to Qdrant
- ☁️ Run from local machine pointing at prod `DATABASE_URL` + `QDRANT_URL`. No CI/CD needed for data ops at MVP.
- ✅ Both scripts finish → "Indexed 144/144". Qdrant dashboard shows 144 vectors.

---

### P4 — Travel Engine (Intelligence Layer)
**4 days · 6 steps**

> This phase builds the destination-agnostic planning rules before the LangGraph nodes use them.  
> Rules here. Logic here. Nodes are thin wrappers.

#### 4.1 travel_engine/travel_rules.py — constants + configuration
- `MAX_PLACES_PER_DAY = 6`
- `MIN_TRAVEL_BUFFER_MIN = 30`
- `VISIT_DURATION_BY_CATEGORY`: monastery=45min, viewpoint=20min, museum=60min, trek=180min
- `CATEGORY_WEIGHTS`: photography=1.4, offbeat=1.3, viewpoint=1.2
- `MORNING_ONLY_CATEGORIES`: ["viewpoint", "sunrise_point"] — Tiger Hill is a morning-only visit
- `AVOID_SAME_DAY_PAIRS`: [("monastery","monastery")] — don't stack same category
- `MAX_DAILY_TRAVEL_MIN = 180` — 3 hours travel per day maximum
- 🏗️ **Configuration Object** — rules are data, not logic. Easily editable without touching algorithms.
- ✅ `from src.travel_engine.travel_rules import MAX_PLACES_PER_DAY` → 6

#### 4.2 travel_engine/place_selector.py — which places? why? what's excluded?
- `select_places(candidates, preferences, destination) → list[ScoredPlace]`
- Apply `CATEGORY_WEIGHTS` to raw Qdrant scores
- Exclusion rules: morning-only places excluded if no morning slot available
- Budget filter: luxury places filtered out on budget preference
- Conflict filter: remove one of a same-day pair that violates `AVOID_SAME_DAY_PAIRS`
- `explain_selection(place, score_breakdown) → str` — why was this place chosen? (logged to evaluation)
- 🏗️ **Strategy Pattern** — selection criteria configurable, testable in isolation
- ✅ `select_places(36 candidates, {interests:["photography"]})` → photography places ranked higher, budget conflicts removed

#### 4.3 travel_engine/day_allocator.py — how many places per day?
- `allocate_days(selected_places, days, preferences) → list[list[ScoredPlace]]`
- Calculate time budget per day: `8hr - travel_buffer = available_visit_time`
- Assign places until day time budget exhausted or `MAX_PLACES_PER_DAY` reached
- Geographic pre-clustering: places within 10km radius seeded into same day candidate pool
- Output: `[[day1_candidates], [day2_candidates], ...]` — not yet ordered
- ✅ `allocate_days(18 places, 3)` → 3 lists, each ≤6 places, total visit time per day < 8hrs

#### 4.4 travel_engine/route_optimizer.py — what order? how much travel time?
- `optimize_route(day_places, origin_lat, origin_lng) → list[OrderedStop]`
- Greedy nearest-neighbour: start from place furthest from accommodation center, add nearest unvisited
- Fetch OSRM travel times between consecutive stops
- If total travel > `MAX_DAILY_TRAVEL_MIN` → drop lowest-scored stop and retry
- `OrderedStop`: place, order, travel_time_from_prev_min, arrival_note (e.g. "Start early — 45min drive")
- 🏗️ **Template Method** — optimize_route defines the algorithm skeleton, OSRM call is injectable
- 🚨 OSRM unavailable → use haversine straight-line × 1.4 factor (road distance heuristic). Log warning.
- ✅ `optimize_route(day1_places)` → ordered stops with travel times, total travel < 180min

#### 4.5 travel_engine/trip_validator.py — is this a good trip?
- `validate_trip(itinerary) → ValidationResult(passed, warnings, errors)`
- Rules checked:
  - Total daily travel < `MAX_DAILY_TRAVEL_MIN`
  - No place repeated across days
  - Morning-only places in morning slots (order ≤ 2)
  - At least one "anchor" attraction per day (score > 0.7)
  - Geographic coherence: std deviation of day's place coordinates < threshold
- Returns warnings (non-blocking) and errors (blocking)
- 🏗️ **Chain of Responsibility** — each rule is a separate check function, easy to add/remove rules
- ✅ `validate_trip(good_itinerary)` → `errors=[], warnings=[]`. `validate_trip(bad_itinerary)` → specific error messages.

#### 4.6 Wire travel_engine into planner nodes — integration test
- `planner/graph/nodes/ranking.py` → calls `place_selector.select_places()`
- `planner/graph/nodes/route_planner.py` → calls `day_allocator.allocate_days()` + `route_optimizer.optimize_route()`
- `planner/graph/nodes/validation.py` → calls `trip_validator.validate_trip()`
- LangGraph nodes become thin: receive state, call travel_engine, update state, return
- ✅ `scripts/test_travel_engine.py` → "3-day Darjeeling trip: all rules passed, travel times realistic"

---

### P5 — AI Planner — LangGraph Agent
**5 days · 9 steps**

#### 5.1 planner/graph/state.py — TravelState TypedDict
- 📦 `langgraph` `langchain-groq`
- Input: `destination_id, destination_name, destination_lat, destination_lng, raw_input, session_id`
- Prefs: `days, budget, interests, include_offbeat, include_trekking`
- Working: `candidate_pois, ranked_pois, route (list[list[OrderedStop]])`
- Output: `itinerary (dict)`
- Meta: `errors (list[str]), warnings (list[str]), trace_id`
- 🏗️ **State Machine** — explicit shared state, no hidden side effects between nodes, fully inspectable
- ✅ `s: TravelState = {}` → no type error

#### 5.2 planner/graph/builder.py — stub graph, all nodes wired
- `StateGraph(TravelState)` with 6 nodes, all stubs
- Edges: `START → preference → poi_retrieval → ranking → route_planner → itinerary → validation → END`
- `build_graph() → CompiledGraph` — module-level singleton
- 🏗️ **Builder Pattern** — graph assembly separated from execution
- 🚨 Graph compilation error (wrong edge name) caught at startup, not first request
- ✅ `graph.invoke(minimal_state)` → all 6 node names in logs in order

#### 5.3 nodes/preference.py — structured LLM parse
- Groq JSON mode: `raw_input → {days, budget, interests, include_offbeat, include_trekking}`
- Validate: days 1–14, interests from controlled list only
- On parse fail: populate `state.errors`, return state
- 🚨 Groq timeout (3s) → retry once → if still fails, use sensible defaults (3 days, mid, no filters). Never blocks user.
- ✅ `node({"raw_input":"3 days offbeat photography"})` → `state.days=3, state.interests=["photography","offbeat"]`

#### 5.4 nodes/poi_retrieval.py — Qdrant + PostGIS fallback
- Build query: `" ".join(state.interests)`
- `top_k = state.days × 12`
- Fetch full Place rows from Postgres for returned IDs
- 🚨 Qdrant unavailable → catch → `PlaceRepository.find_within_radius()`. Log "using geo fallback". No user impact.
- ✅ `node(state photography+offbeat 3 days)` → `state.candidate_pois` has 36 places

#### 5.5 nodes/ranking.py — calls place_selector
- Calls `travel_engine.place_selector.select_places(candidates, preferences, destination)`
- Stores result in `state.ranked_pois`
- Node is ~5 lines — all logic in travel_engine
- ✅ `node(36 candidates)` → 18 selected, photography spots at top

#### 5.6 nodes/route_planner.py — calls day_allocator + route_optimizer
- Calls `day_allocator.allocate_days()` → groups into days
- Calls `route_optimizer.optimize_route()` per day → ordered stops with travel times
- Stores result in `state.route`
- Node is ~10 lines — all logic in travel_engine
- ✅ `node(18 places 3 days)` → `state.route` = 3 lists, geographically grouped, ordered

#### 5.7 nodes/itinerary.py — LLM narrative + OSRM polylines
- LLM (Groq) writes day title + narrative paragraph — structure comes from `state.route`, not LLM
- OSRM called per day sequence → `encoded_polyline` + `total_distance_km` attached
- `get_tracer().trace()` wraps LLM call
- Output per day: `{day, title, narrative, total_distance_km, polyline, places:[{name,lat,lng,order,travel_time_min}]}`
- 🚨 Groq timeout → retry once → template narrative fallback. OSRM fail → straight-line fallback. Never blocks output.
- ✅ Full itinerary dict with narrative, place list, polyline per day

#### 5.8 nodes/validation.py — calls trip_validator + records evaluation
- Calls `travel_engine.trip_validator.validate_trip(state.itinerary)`
- Calls `evaluation.service.record_generation(state, validation_result, timing)` — stores TripEvaluation row
- On validation errors → `state.errors` populated, itinerary flagged `needs_review`
- 🚨 Validation fail → return itinerary with warnings, never 500. Frontend shows itinerary with review note. Evaluation always recorded even on partial failure.
- ✅ `node(valid)` → `errors=[]`. `node(injected bad place)` → `errors=["hallucinated_place"]`

#### 5.9 scripts/test_agent.py — full end-to-end
- Input: destination=Darjeeling, `raw_input="3 days offbeat photography budget"`
- Assert: `errors=[]`, day count=3, all places have lat/lng, validation passed
- Print Langfuse trace URL if keys configured
- ✅ Complete 3-day itinerary JSON, "validation: passed", evaluation row written to DB

---

### P6 — Planner API + Persistence
**3 days · 5 steps**

#### 6.1 trips/ — repository + service
- `TripRepository(BaseRepository[Trip, UUID])`: `list_by_user()`, `list_by_session()`, `get_with_places()`
- `TripService.save_from_state(state, user_id, session_id) → Trip`
- Anonymous trips claimable after login (session_id match)
- 🏗️ **Unit of Work** — Trip + TripPlace written in one transaction, rollback on partial failure
- 🚨 Partial TripPlace insert fail → full rollback. Trip row never exists without its places.
- ✅ Save itinerary → `trip_id` returned → `get_with_places` → all stops present

#### 6.2 planner/router.py — POST /generate streaming SSE
- `POST /api/v1/planner/generate` body: `PlanRequest(destination_id, raw_input, days)`
- `StreamingResponse` content-type `text/event-stream`
- SSE events: `preferences_done` → `pois_found(count)` → `route_ready` → `itinerary_done(data=json)`
- `optional_auth` — guests can plan, registered users get auto-save
- 🚨 Agent error mid-stream → emit `error` SSE event with code + message, close stream cleanly. Never hangs.
- ✅ `curl -N POST /api/v1/planner/generate` → events stream one by one, final `data=` is full JSON

#### 6.3 trips/router.py — CRUD + paginated list + GeoJSON
- `GET /api/v1/trips` → `PaginatedResponse[TripOut]` (require_auth)
- `GET /api/v1/trips/{id}` → `ApiResponse[TripOut]` (optional_auth + ownership)
- `GET /api/v1/trips/{id}/geojson` → GeoJSON FeatureCollection (public — shareable link)
- `DELETE /api/v1/trips/{id}` → 204 (require_auth + ownership)
- 🚨 Accessing another user's trip → 403 (not 404 — don't confirm existence)
- ✅ `GET /api/v1/trips/{id}/geojson` → paste to geojson.io → route renders on map

#### 6.4 core/middleware/rate_limit.py + planner cache
- Rate limiter: 10 req/min per IP on `/planner/generate`. Returns 429 + `Retry-After` header.
- Planner cache key: `sha256(destination_id + sorted_interests + days + budget)` — 1hr TTL
- Dev: in-memory dict. Prod (REDIS_URL present): Redis SET.
- ☁️ Prod: `REDIS_URL=Upstash` free tier. Groq API calls drop dramatically for popular destinations.
- 🚨 Rate limiter error → fail open (allow request) + log warning. Cache unavailable → skip cache, run agent fresh.
- ✅ Same input twice → 2nd response instant, no agent log lines. 11th rapid request → 429.

#### 6.5 Backend ship checklist
- [ ] `GET /api/v1/destinations/search?q=Darjeeling` → geocoded result
- [ ] `GET /api/v1/places?destination_id=...&page=2` → `PaginatedResponse` with `has_next/has_prev`
- [ ] `POST /api/v1/planner/generate` → SSE stream, final event = full itinerary JSON
- [ ] `GET /api/v1/trips/{id}/geojson` → valid GeoJSON, renders on geojson.io
- [ ] All errors return `ErrorResponse`. All lists return `PaginatedResponse`.
- [ ] `evaluation` table has rows after each generation
- [ ] `travel_engine` rules pass for Darjeeling + Manali + Goa
- [ ] `pytest tests/ -v` → all green
- [ ] `docker compose up` from clean state → works
- [ ] No hardcoded values in any file — all from `get_settings()`
- [ ] Set `DATABASE_URL`, `QDRANT_URL`, `REDIS_URL`, `GROQ_API_KEY`, `SECRET_KEY` in prod env → zero code changes needed

---

## LLD Pattern Reference

| Pattern | Where used |
|---------|-----------|
| Modular Monolith | Overall project structure |
| Singleton | `get_settings()`, `get_qdrant_client()`, `build_graph()` |
| App Factory | `create_app()` in main.py |
| Generic Repository | `BaseRepository[M, ID]` |
| Unit of Work | Session per request, Trip+TripPlace transaction |
| Specification Pattern | `filters: dict` in repo queries |
| Service Layer | Router → Service → Repository only |
| Gateway Pattern | `geo/geocoder.py`, `geo/overpass.py`, `geo/osrm.py` |
| Cache-Aside | Destinations lookup, planner result cache |
| Strategy Pattern | `embed_text()`, `score_place()`, `place_selector` |
| Null Object Pattern | `NoOpTracer` |
| Response Envelope | `ApiResponse[T]`, `PaginatedResponse[T]` |
| Exception Hierarchy | `WandrError` → domain exceptions |
| Chain of Responsibility | Middleware stack, `trip_validator` rules |
| State Machine | `TravelState` through LangGraph |
| Builder Pattern | `build_graph()` |
| Configuration Object | `travel_rules.py` |
| Template Method | `route_optimizer` with injectable OSRM call |

---

## Failure Boundary Summary

| Layer | Failure | Response |
|-------|---------|----------|
| DB connection | Timeout / unreachable | `ExternalServiceError` 502, pool_pre_ping recycles stale connections |
| DB migration | Failed migration | Auto-rollback, running app unaffected |
| Nominatim | Timeout | Return None → `DestinationNotFound` 404. Not critical if destinations pre-seeded. |
| Overpass | Timeout | Log + partial results. Script-only, zero live app impact. |
| OSRM | Timeout | Straight-line fallback × 1.4 factor. Itinerary still valid. |
| Qdrant | Unreachable | `search_available=False`, PostGIS radius fallback in planner |
| Groq (preference) | Timeout | Retry once → sensible defaults. Never blocks user. |
| Groq (itinerary) | Timeout | Retry once → template narrative. Never blocks output. |
| Groq (enrichment) | Rate limit | Exponential backoff 3 retries in batch script |
| Langfuse | Any error | Caught as warning. Never propagates to request. |
| JWT | Expired / malformed | 401 ErrorResponse. Never 422 or 500. |
| Auth callback | OAuth failure | Redirect to `/auth/error`. Never 500 page. |
| Rate limiter | Internal error | Fail open (allow request) + log warning |
| Redis cache | Unavailable | Skip cache, run agent fresh. Cache is acceleration not dependency. |
| Planner agent | Mid-stream error | Emit `error` SSE event, close stream cleanly. Never hangs. |
| Trip save | Partial insert | Full transaction rollback. Trip never exists without its places. |
| Validation | Rules fail | Return itinerary with `warnings`, never 500. Always record evaluation. |

---

## Package Install Order

Packages are installed at the step they are first needed. Never before.

| Step | Package | Reason |
|------|---------|--------|
| 0.2 | `pydantic-settings` | Settings class |
| 0.4 | `structlog` | Logging |
| 0.5 | `langfuse` | AI tracing |
| 0.9 | `fastapi` `uvicorn[standard]` | App server |
| 1.1 | `sqlalchemy[asyncio]` `asyncpg` | Async DB |
| 1.3 | `alembic` `geoalchemy2` | Migrations + PostGIS types |
| 1.6 | `python-jose[cryptography]` | JWT |
| 1.7 | `httpx` | External HTTP (OAuth + geo calls) |
| 3.1 | `qdrant-client` | Vector search |
| 3.2 | `sentence-transformers` | Embeddings |
| 3.3 | `groq` | LLM |
| 5.1 | `langgraph` `langchain-groq` | Agent framework |
| 6.5 | `pytest` `pytest-asyncio` `pytest-mock` | Tests |