# Wandr — AI Agent Context

> **Read this first every session.** Then `AGENT.md` (rules), then the current step in `docs/steps/step1.md` (or blueprint).
> Deep reference: `docs/app/system.md` (architecture), `docs/app/lld.md` (patterns).
> Developer playbook (OpenSpec workflow + example prompts): `docs/spec.md`

**Last updated:** 2026-07-17 · **Phase:** P1 · **Next step:** 1.5

---

## Current state (one line)

P0 complete. P1 in progress — core DB models + migration 002 applied (6 tables); BaseRepository, auth, middleware not started.

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
| 1.5–1.12 | ⬜ Pending | `BaseRepository`, JWT, auth, middleware, tests — see `docs/steps/step1.md` |

---

## Implemented modules (real code)

| Module | Exports / notes |
|--------|-----------------|
| `src/config.py` | `get_settings()` — all env vars |
| `src/core/observability/logging.py` | `configure_logging()`, `get_logger()` |
| `src/core/observability/tracing.py` | `get_tracer()`, `flush_tracer()` |
| `src/core/llm/client.py` | `chat_completion()`, `chat_with_tools()` — **only** litellm import |
| `src/core/pagination.py` | `PageParams`, `PaginatedResponse[T]`, `paginate()` |
| `src/core/responses.py` | `ApiResponse[T]`, `ErrorResponse` |
| `src/core/exceptions.py` | `WandrError` tree |
| `src/core/database/base.py` | `Base`, mixins (SQLAlchemy 2.0 `Mapped[]`) |
| `src/core/database/session.py` | `get_engine()`, `get_session_factory()`, `get_db()`, `ping_db()`, `dispose_engine()` |
| `src/main.py` | `create_app()`, lifespan, global handlers, health endpoint |
| `alembic/env.py` | Async Alembic + `include_object` filter + all model imports |
| `alembic/versions/001_enable_postgis.py` | PostGIS + uuid-ossp extensions |
| `alembic/versions/20260717_*_create_all_tables.py` | Migration 002 — 6 core tables |
| `src/auth/models.py` | `User` |
| `src/destinations/models.py` | `Destination` |
| `src/places/models.py` | `Place` (Geometry POINT SRID 4326) |
| `src/trips/models.py` | `TripStatus`, `Trip`, `TripPlace` |
| `src/evaluation/models.py` | `TripEvaluation` |

**Tests:** `tests/core/test_exceptions.py`

**Scripts:** `scripts/test_db_conn.py` (DB smoke test)

---

## Stubs only (do not assume implemented)

All other `src/**/*.py` files (auth/destinations/places/trips/evaluation except `models.py`, planner, geo, search, travel_engine, security, middleware, `base_repository.py`) are step 0.1 placeholders — one-line docstrings, no logic.

---

## Live endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/health` | None |

No domain routers registered in `main.py` yet.

---

## Local dev quick ref

```bash
docker compose up -d          # Postgres :5433, Qdrant :6335
uvicorn src.main:app --reload
python scripts/test_db_conn.py
alembic upgrade head          # run migrations (deploy/CLI only — not at app startup)
```

- `DATABASE_URL=postgresql+asyncpg://wandr:wandr@localhost:5433/wandr` (port **5433**, not 5432)
- `QDRANT_URL=http://localhost:6335`
- `.env` must have a **bare** `DATABASE_URL` value — no comment prefix on the same line

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
