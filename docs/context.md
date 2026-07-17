# Wandr — AI Agent Context

> **Read this first every session.** Then `AGENT.md` (rules), then the current step in `docs/steps/step1.md` (or blueprint).
> Deep reference: `docs/app/system.md` (architecture), `docs/app/lld.md` (patterns).
> Developer playbook (OpenSpec workflow + example prompts): `docs/spec.md`

**Last updated:** 2026-07-05 · **Phase:** P1 · **Next step:** 1.3

---

## Current state (one line)

P0 complete. P1 in progress — DB base + async session done; Alembic, models, auth, middleware not started. Domain packages exist as **empty stubs** only.

---

## Progress

| Step | Status | Key deliverable |
|------|--------|-----------------|
| 0.1–0.10 | ✅ Done | Scaffold, config, logging, tracing, LLM gateway, pagination, responses, exceptions, FastAPI app + `/api/v1/health` |
| 1.1 | ✅ Done | `src/core/database/base.py` — `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` |
| 1.2 | ✅ Done | `src/core/database/session.py` — pool, `get_db()`, `scripts/test_db_conn.py` |
| 1.3 | ⏳ Next | Alembic async setup + migration 001 PostGIS (`alembic`, `geoalchemy2`) |
| 1.4–1.12 | ⬜ Pending | Models, `BaseRepository`, JWT, auth, middleware, tests — see `docs/steps/step1.md` |

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

**Tests:** `tests/core/test_exceptions.py`

**Scripts:** `scripts/test_db_conn.py` (DB smoke test)

---

## Stubs only (do not assume implemented)

All other `src/**/*.py` files (auth, destinations, places, trips, planner, geo, search, travel_engine, evaluation, security, middleware, `base_repository.py`) are step 0.1 placeholders — one-line docstrings, no logic.

`alembic/env.py` is a placeholder until step 1.3.

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
