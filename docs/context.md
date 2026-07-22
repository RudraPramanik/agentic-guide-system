# Wandr — AI Agent Context

> **Read this first every session.** Then `AGENT.md` (rules), then the current step in `docs/steps/step2.md` (or blueprint).
> Deep reference: `docs/app/system.md` (architecture), `docs/app/lld.md` (patterns).
> Junior map (layers / files / imports): `docs/app/documentation.md` → `docs/manual/` (refresh on phase end or every 4–5 steps — not every step).
> P2 study guide (engineering + interview Q&A): `docs/app/p2guide.md` · books: `docs/books/p2-references.md`
> Developer playbook (OpenSpec workflow + example prompts): `docs/spec.md`

**Last updated:** 2026-07-22 · **Phase:** P2 in progress · **Next step:** P2.4

---

## Current state (one line)

P2.6a+2.6b done — destination schemas/exceptions + atomic upsert repo + cache-aside search service; next is P2.4 seed script.

---

## Progress

| Step | Status | Key deliverable |
|------|--------|-----------------|
| 0.1–0.10 | ✅ Done | Scaffold, config, logging, tracing, LLM gateway, pagination, responses, exceptions, FastAPI app + `/api/v1/health` |
| 1.1 | ✅ Done | `src/core/database/base.py` — `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` |
| 1.2 | ✅ Done | `src/core/database/session.py` — pool, `get_db()`, `scripts/test_db_conn.py` |
| 1.3 | ✅ Done | Alembic async env + migration 001 PostGIS (`alembic`, `geoalchemy2`) |
| 1.4a | ✅ Done | User + Destination models |
| 1.4b | ✅ Done | Place + Trip + TripPlace models (PostGIS POINT, TripStatus enum) |
| 1.4c | ✅ Done | TripEvaluation model |
| 1.4d | ✅ Done | Migration 002 — 6 tables + `trip_status` enum |
| 1.5 | ✅ Done | `BaseRepository` — soft-delete aware CRUD, flush-only writes |
| 1.6 | ✅ Done | JWT + `require_auth` / `optional_auth` (Bearer or `wandr_token` cookie) |
| 1.7a | ✅ Done | Auth schemas + exceptions |
| 1.7b | ✅ Done | `UserRepository` + `AuthService` (Google OAuth, upsert commits) |
| 1.7c | ✅ Done | Auth router + `main.py` registration |
| 1.8 | ✅ Done | `RequestLoggingMiddleware` — `X-Request-ID` + latency logs |
| 1.9 | ✅ Done | `TripEditEvent` + `EditType` model, migration 003 `trip_edit_events` |
| 1.10 | ✅ Done | `RateLimitMiddleware` — config-driven limits, fail-open, planner 10/min |
| 1.11 | ✅ Done | pytest harness + auth/core/middleware tests (37 passing) |
| 1.12 | ✅ Done | `scripts/test_p1_smoke.py` — PostGIS, soft-delete, TripEditEvent CASCADE |
| 2.1 | ✅ Done | `geo/schemas` + `geo/geocoder` — Nominatim gateway, dict cache, 1 req/sec throttle |
| 2.2 | ✅ Done | `geo/overpass` — Overpass POI scraper, category map, dedupe, `[]` on failure |
| 2.3 | ✅ Done | `places/repository` — atomic OSM upsert, geography radius, list/count by destination |
| 2.6a | ✅ Done | destinations schemas + `DestinationNotFoundError` |
| 2.6b | ✅ Done | `DestinationRepository` atomic upsert + `DestinationService` cache-aside search |

---

## Implemented modules (real code)

| Module | Exports / notes |
|--------|-----------------|
| `src/config.py` | `get_settings()` — env vars incl. Google OAuth, JWT TTL, rate limit, `NOMINATIM_BASE_URL`, `OVERPASS_API_URL` |
| `src/core/observability/logging.py` | `configure_logging()`, `get_logger()` |
| `src/core/observability/tracing.py` | `get_tracer()`, `flush_tracer()` |
| `src/core/llm/client.py` | `chat_completion()`, `chat_with_tools()` — **only** litellm import |
| `src/core/pagination.py` | `PageParams`, `PaginatedResponse[T]`, `paginate()` |
| `src/core/responses.py` | `ApiResponse[T]`, `ErrorResponse` |
| `src/core/exceptions.py` | `WandrError` tree |
| `src/core/database/base.py` | `Base`, mixins (SQLAlchemy 2.0 `Mapped[]`) |
| `src/core/database/session.py` | `get_engine()`, `get_session_factory()`, `get_db()`, `ping_db()`, `dispose_engine()` |
| `src/core/database/base_repository.py` | `BaseRepository[ModelT, IDT]` — soft-delete, paginate, flush-only writes |
| `src/core/security/jwt.py` | `TokenPayload`, `create_access_token()`, `verify_token()` |
| `src/core/security/permissions.py` | `require_auth`, `optional_auth`, `get_current_user_id` |
| `src/core/middleware/logging.py` | `RequestLoggingMiddleware` — `X-Request-ID`, structlog context, latency |
| `src/core/middleware/rate_limit.py` | `RateLimitMiddleware`, `InMemoryRateLimiter`, `RateLimiterBackend` protocol |
| `src/main.py` | `create_app()`, lifespan, logging + rate limit middleware, global handlers, health + auth router |
| `alembic/env.py` | Async Alembic + `include_object` filter + all model imports |
| `alembic/versions/001_enable_postgis.py` | PostGIS + uuid-ossp extensions |
| `alembic/versions/20260717_*_create_all_tables.py` | Migration 002 — 6 core tables |
| `alembic/versions/20260721_*_add_trip_edit_events.py` | Migration 003 — `trip_edit_events` + `edit_type` enum |
| `src/auth/models.py` | `User` |
| `src/auth/schemas.py` | `UserOut`, `AuthMeResponse`, `TokenResponse`, `GoogleCallbackParams` |
| `src/auth/exceptions.py` | `GoogleOAuthError`, `InvalidTokenError`, `AccountInactiveError` |
| `src/auth/repository.py` | `UserRepository` |
| `src/auth/service.py` | `AuthService` — upsert, Google exchange/userinfo |
| `src/auth/router.py` | `/api/v1/auth/google|callback|me|logout` |
| `src/destinations/models.py` | `Destination` |
| `src/destinations/schemas.py` | `DestinationOut`, `DestinationSearchQuery`, `DestinationReadinessOut` |
| `src/destinations/exceptions.py` | `DestinationNotFoundError` (404) |
| `src/destinations/repository.py` | `DestinationRepository` — atomic geocode upsert, ILIKE search |
| `src/destinations/service.py` | `DestinationService` — cache-aside search (DB → geocode → upsert) |
| `src/places/models.py` | `Place` (Geometry POINT SRID 4326) |
| `src/places/repository.py` | `PlaceRepository` — `upsert_from_poi`, `find_within_radius`, `list_by_destination`, `count_by_destination` |
| `src/trips/models.py` | `TripStatus`, `Trip`, `TripPlace`, `EditType`, `TripEditEvent` |
| `src/evaluation/models.py` | `TripEvaluation` |
| `src/geo/schemas.py` | `GeocodedPlace`, `RawPOI`, `RouteResult` |
| `src/geo/geocoder.py` | `geocode()` — Nominatim gateway; process-local dict cache + 1 req/sec throttle |
| `src/geo/overpass.py` | `fetch_pois()` — Overpass gateway; form `data=` POST; 5xx/timeout retry; `[]` fallback |

**Tests:** `tests/core/test_*.py`, `tests/auth/test_*.py` — run `python -m pytest tests/ -v` (DB `wandr_test`)

**Scripts:** `scripts/test_db_conn.py`, `scripts/test_p1_smoke.py`, `scripts/test_geocoder.py`, `scripts/test_overpass.py`

**TODO (P6):** geocoder cache + Nominatim throttle are per-process; back with Redis when `REDIS_URL` is wired for the rate limiter.

---

## Stubs only (do not assume implemented)

All other `src/**/*.py` files (destinations except `models.py` + schemas/exceptions/repository/service; places except `models.py` + `repository.py`; trips/evaluation except `models.py`; `geo/osrm.py`; planner, search, travel_engine; `src/auth/dependencies.py`) are step 0.1 placeholders — one-line docstrings, no logic.

---

## Live endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/health` | None |
| GET | `/api/v1/auth/google` | None (redirect or not-configured message) |
| GET | `/api/v1/auth/callback` | None (OAuth redirect) |
| GET | `/api/v1/auth/me` | Optional (guest or cookie/Bearer) |
| POST | `/api/v1/auth/logout` | None |

---

## Local dev quick ref

```bash
docker compose up -d          # Postgres :5433, Qdrant :6335
uvicorn src.main:app --reload
python scripts/test_db_conn.py
python scripts/test_p1_smoke.py
python scripts/test_geocoder.py "Darjeeling"   # needs PYTHONPATH=project root if imports fail
python scripts/test_overpass.py 27.041 88.263 30   # public Overpass may 504; override OVERPASS_API_URL if needed
alembic upgrade head          # run migrations (deploy/CLI only — not at app startup)
python -m pytest tests/ -v
```

- `DATABASE_URL=postgresql+asyncpg://wandr:wandr@localhost:5433/wandr` (port **5433**, not 5432)
- `QDRANT_URL=http://localhost:6335`
- `.env` must have a **bare** `DATABASE_URL` value — no comment prefix on the same line
- Geo: `NOMINATIM_BASE_URL`, `OVERPASS_API_URL`, `NOMINATIM_USER_AGENT` via `get_settings()`
- Overpass: `read=90s` + retry on 5xx (amendment vs step `read=30`); failure → `[]`

---

## Hard rules (reminder)

See `AGENT.md` for full list. Non-negotiable:

- Router → Service → Repository only
- LLM only via `src/core/llm/client.py`
- Geo only via `src/geo/`
- `travel_engine/` — pure Python, no I/O
- All env via `get_settings()`
- Endpoints return `ApiResponse[T]` or `PaginatedResponse[T]`

---

## After completing a step

Update this file: bump **Last updated**, set **Next step**, mark step ✅ in Progress, add row to Implemented modules if new real code landed. See `.cursorrules`.

Refresh the **developer manual** (`docs/app/documentation.md` + `docs/manual/`) only when a full phase ends **or** every 4–5 validated steps since its “Through step” marker — see `docs/manual/06-maintenance.md`.
