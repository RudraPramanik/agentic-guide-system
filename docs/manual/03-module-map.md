# 03 — Module map (through P2.2)

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [02-layers](02-layers.md)

Source of truth for “real vs stub”: [`docs/context.md`](../context.md). This page is a navigable snapshot as of **P2.2**.

---

## Package tree (mental map)

```text
src/
├── main.py                 # App factory ✅
├── config.py               # Settings ✅
├── auth/                   # Google OAuth + JWT cookie flow ✅ (deps.py stub)
├── geo/                    # schemas, geocoder, overpass ✅ · osrm ❌ stub
├── core/                   # shared infrastructure ✅
│   ├── database/           # base, session, BaseRepository ✅
│   ├── security/           # jwt, permissions ✅
│   ├── middleware/         # logging, rate_limit ✅
│   ├── observability/      # logging, tracing ✅
│   ├── llm/                # litellm gateway ✅
│   ├── pagination.py ✅
│   ├── responses.py ✅
│   └── exceptions.py ✅
├── destinations/           # models ✅ · service/repo/router ❌ stubs
├── places/                 # models ✅ · repo/service/router ❌ stubs
├── trips/                  # models ✅ · rest ❌ stubs
├── evaluation/             # models ✅ · rest ❌ stubs
├── planner/                # ❌ stubs (LangGraph later)
├── search/                 # ❌ stubs (Qdrant later)
└── travel_engine/          # ❌ stubs (pure Python later)

alembic/                    # migrations 001–003 ✅
scripts/                    # smoke + geo CLIs ✅
tests/                      # core + auth ✅
```

---

## Real modules (implemented)

### App & config

| Path | Exports / role |
|------|----------------|
| `src/main.py` | `create_app()`, lifespan, middleware, handlers, health + auth router |
| `src/config.py` | `get_settings()` — DB, OAuth, JWT, rate limit, Nominatim/Overpass URLs |

### Core

| Path | Exports / role |
|------|----------------|
| `src/core/observability/logging.py` | `configure_logging()`, `get_logger()` |
| `src/core/observability/tracing.py` | `get_tracer()`, `flush_tracer()` |
| `src/core/llm/client.py` | `chat_completion()`, `chat_with_tools()` — **only** litellm import site |
| `src/core/pagination.py` | `PageParams`, `PaginatedResponse[T]`, `paginate()` |
| `src/core/responses.py` | `ApiResponse[T]`, `ErrorResponse` |
| `src/core/exceptions.py` | `WandrError` hierarchy |
| `src/core/database/base.py` | `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` |
| `src/core/database/session.py` | `get_engine()`, `get_session_factory()`, `get_db()`, `ping_db()`, `dispose_engine()` |
| `src/core/database/base_repository.py` | `BaseRepository[ModelT, IDT]` — soft-delete, flush-only |
| `src/core/security/jwt.py` | `TokenPayload`, `create_access_token()`, `verify_token()` |
| `src/core/security/permissions.py` | `require_auth`, `optional_auth`, `get_current_user_id` |
| `src/core/middleware/logging.py` | `RequestLoggingMiddleware` |
| `src/core/middleware/rate_limit.py` | `RateLimitMiddleware`, `InMemoryRateLimiter` |

### Auth

| Path | Exports / role |
|------|----------------|
| `src/auth/models.py` | `User` |
| `src/auth/schemas.py` | `UserOut`, `AuthMeResponse`, `TokenResponse`, … |
| `src/auth/exceptions.py` | OAuth / token / inactive errors |
| `src/auth/repository.py` | `UserRepository` |
| `src/auth/service.py` | `AuthService` — Google exchange, upsert |
| `src/auth/router.py` | `/api/v1/auth/google\|callback\|me\|logout` |

### Domain models only (no services yet)

| Path | Model |
|------|-------|
| `src/destinations/models.py` | `Destination` |
| `src/places/models.py` | `Place` (PostGIS POINT) |
| `src/trips/models.py` | `Trip`, `TripPlace`, `TripEditEvent`, enums |
| `src/evaluation/models.py` | `TripEvaluation` |

### Geo

| Path | Exports / role |
|------|----------------|
| `src/geo/schemas.py` | `GeocodedPlace`, `RawPOI`, `RouteResult` |
| `src/geo/geocoder.py` | `geocode()` |
| `src/geo/overpass.py` | `fetch_pois()` |

### Migrations & tooling

| Path | Role |
|------|------|
| `alembic/env.py` | Async Alembic + model imports |
| `alembic/versions/001_enable_postgis.py` | PostGIS + uuid-ossp |
| `alembic/versions/20260717_*_create_all_tables.py` | Core tables |
| `alembic/versions/20260721_*_add_trip_edit_events.py` | `trip_edit_events` |
| `scripts/test_db_conn.py` | DB ping |
| `scripts/test_p1_smoke.py` | P1 smoke |
| `scripts/test_geocoder.py` | Live Nominatim CLI |
| `scripts/test_overpass.py` | Live Overpass CLI |
| `tests/core/`, `tests/auth/` | pytest suite |

---

## Stubs only (no public API — do not invent imports)

Treat these as **placeholders** until `context.md` moves them to Implemented:

| Area | Notes |
|------|-------|
| `src/geo/osrm.py` | Routing gateway — step 2.5 |
| `src/auth/dependencies.py` | Unused placeholder |
| `src/destinations/*` except `models.py` | Repo/service/router later (2.6+) |
| `src/places/*` except `models.py` | Repo next (2.3) |
| `src/trips/*` except `models.py` | Trip APIs later |
| `src/evaluation/*` except `models.py` | Eval recording later |
| `src/planner/**` | LangGraph agent — later phases |
| `src/search/**` | Qdrant / embeddings — later |
| `src/travel_engine/**` | Pure scheduling logic — later |

If unsure: open the file. Stubs are ~1-line docstrings.

Next: [04 — Imports & wiring](04-imports-and-wiring.md)
