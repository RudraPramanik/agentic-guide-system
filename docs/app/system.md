# Wandr Backend — System Context

> Production-grade AI travel planner. Modular monolith. Phase-gated tool-loop agent.
> For coding guardrails see [`AGENT.md`](../../AGENT.md). For build steps see [`docs/blueprint_final.md`](../blueprint_final.md).

## What Wandr Does

Wandr generates structured multi-day travel itineraries. Users describe preferences in natural language; the backend:

1. Resolves destinations and checks data readiness
2. Searches and ranks places (vector + geo fallback)
3. Builds routes and day schedules via deterministic `travel_engine` logic
4. Uses a bounded LangGraph agent with typed tools for orchestration
5. Writes narrative copy via LLM (outside the tool loop)
6. Persists trips and records every generation/edit for evaluation

**Core principle:** structure from code, narrative from LLM. Place IDs, coordinates, stop order, and times never come from free-form LLM output.

## Architecture Overview

```
Client (HTTP/SSE)
    │
    ▼
FastAPI Routers          ← ApiResponse[T] envelope, no raw dicts
    │
    ▼
Domain Services          ← business logic, orchestration
    │
    ├──► Repositories    ← SQLAlchemy async, PostGIS
    ├──► travel_engine/  ← pure Python, no I/O (routing injected)
    ├──► planner/tools/  ← typed tool registry + execute_tool()
    ├──► geo/            ← Nominatim, Overpass, OSRM gateways
    ├──► search/         ← Qdrant + embeddings
    ├──► core/llm/       ← LiteLLM gateway (only LLM entry point)
    └──► evaluation/     ← every generation and edit recorded
```

## Repository Layout

| Path | Role |
|------|------|
| `src/config.py` | Single source of truth for env vars (`get_settings()`) |
| `src/core/` | Cross-cutting infra: DB, security, middleware, observability, LLM |
| `src/auth/` | JWT auth, user management |
| `src/destinations/` | Destination catalog + readiness scoring |
| `src/places/` | POI storage and enrichment |
| `src/trips/` | Trip CRUD, edits, persistence |
| `src/planner/` | LangGraph agent, tools, SSE streaming |
| `src/travel_engine/` | Pure routing/scheduling/validation algorithms |
| `src/geo/` | External geo service gateways |
| `src/search/` | Vector search and embeddings |
| `src/evaluation/` | Generation quality tracking |
| `scripts/` | Seeding, indexing, local test harnesses |
| `tests/` | Pytest suites per domain |

## Local Development Infrastructure

`docker-compose.yml` provides **local dev only** (never production):

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `wandr_postgres` | `postgis/postgis:16-3.4` | 5433 | PostgreSQL + PostGIS (host port 5433 avoids conflict with local Postgres on 5432) |
| `wandr_qdrant` | `qdrant/qdrant:latest` | 6335/6336 | Vector search (host port 6335 avoids conflict with other Qdrant on 6333) |

Redis is feature-flagged off in dev (`REDIS_URL` empty → in-memory fallback).

Production uses hosted services injected via environment variables.

## Configuration

All environment variables are defined in `src/config.py` (`Settings` class) and loaded once via `@lru_cache` `get_settings()`.

**Never** call `os.environ.get()` outside `config.py`.

Key groups: Core, Database, Vector search, Cache, LLM, Planner agent bounds, Observability, Geo.

See `.env.example` for the full key list with placeholder values.

## Observability (implemented)

### Structured logging — step 0.4

Module: `src/core/observability/logging.py`

- `configure_logging()` — called once in app lifespan; idempotent
- `get_logger()` — convenience alias for `structlog.get_logger()`
- **Development:** colored `ConsoleRenderer` to stdout
- **Production:** `JSONRenderer` for log aggregation (Datadog, CloudWatch, etc.)
- **Context propagation:** middleware calls `bind_contextvars(request_id=...)`; every log line in that request inherits it automatically

Processing chain: `merge_contextvars` → `add_log_level` → `TimeStamper(iso)` → renderer.

### Tracing — step 0.5

Module: `src/core/observability/tracing.py`

- `get_tracer()` → `Langfuse` when both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set; otherwise `NoOpTracer`
- `flush_tracer()` — called on app shutdown lifespan
- **Null Object Pattern:** callers never branch on `if tracer:` — `NoOpTracer` implements the same interface (`trace`, `span`, `generation`, `update`, `end`, `flush`)
- Init and flush errors are caught, logged as warnings via structlog, never propagated to requests
- Result cached in a module-level variable (first call only)

Package: `langfuse==2.60.10` (latest v2 line; v3+ removed the `trace()` client API this step depends on).

### LLM gateway — step 0.6

Module: `src/core/llm/client.py`

- **Only** module that imports `litellm` — all LLM calls go through here
- `chat_completion(messages, model?, response_format?)` → plain string
- `chat_with_tools(messages, tools, tool_choice?, model?)` → `LLMToolResponse` with `tool_calls` or `content`
- Provider swappable via `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE` in `config.py`
- Tenacity retry: `LLM_MAX_RETRIES` attempts, exponential wait 2–30s, on timeout/rate-limit only
- Exhausted retries → `WandrLLMError` (503) — caught by planner nodes, never a raw 500

Packages: `litellm==1.89.1`, `tenacity==9.1.4`

### Pagination — step 0.7

Module: `src/core/pagination.py`

- `PageParams` — `Depends()` query params: `page=1`, `size=20` (max 100), `offset` property
- `PaginatedResponse[T]` — list envelope with auto-computed `pages`, `has_next`, `has_prev`
- `paginate(items, total, params)` — builds response from repo results + params
- No DB logic — routers/services pass `offset`/`size` to repos, wrap with `paginate()`

### Response envelopes — step 0.8

Module: `src/core/responses.py`

- `ApiResponse[T]` — success wrapper: `success=True`, `data`, optional `message`
- `ErrorResponse` — error wrapper: `success=False`, `code`, `message`, optional `details`
- Every single-resource endpoint returns `ApiResponse[T]`; global handler returns `ErrorResponse` (wired in step 0.10)

### Exception hierarchy — step 0.9

Module: `src/core/exceptions.py`

- `WandrError` base with `code`, `message`, `status_code`, `details`
- Domain subclasses: `NotFoundError` (404), `UnauthorizedError` (401), `ForbiddenError` (403), `ExternalServiceError` (502), `WandrLLMError` (503)
- `ExternalServiceError` auto-injects `service` into `details`
- `WandrLLMError` raised only by LLM gateway; caught in planner nodes with fallbacks
- Tests: `tests/core/test_exceptions.py`

### FastAPI app — step 0.10

Module: `src/main.py`

- **App Factory:** `create_app() → FastAPI`; module-level `app = create_app()` for `uvicorn src.main:app`
- **Lifespan startup:** `configure_logging()` → `wandr.startup` log → DB `SELECT 1` ping (fail-fast `SystemExit(1)`) → Qdrant `/healthz` ping (warning only if down)
- **Lifespan shutdown:** `flush_tracer()` → `wandr.shutdown` log → `dispose_engine()`
- **Global exception handlers:** `WandrError` → `ErrorResponse` with exception status; `RequestValidationError` → 422; unhandled `Exception` → 500 with generic message (full traceback logged server-side via `exc_info=True`)
- **`GET /api/v1/health`:** no auth; returns `ApiResponse` with `status`, `env`, `version`; 503 if DB unreachable at request time
- No domain routers registered yet; no `X-Request-ID` header (step 1.8)

Packages: `fastapi==0.137.1`, `uvicorn[standard]==0.49.0`, `sqlalchemy[asyncio]==2.0.51`, `asyncpg==0.31.0`

### Database foundation — steps 1.1–1.2

#### Declarative base + mixins — step 1.1

Module: `src/core/database/base.py`

- `Base` — SQLAlchemy 2.0 `DeclarativeBase` (no `__abstract__` on Base itself)
- `UUIDMixin` — `id: Mapped[uuid.UUID]`, `UUID(as_uuid=True)`, `primary_key=True`, Python `default=uuid.uuid4` (not `server_default` — ID known before INSERT for same-transaction FKs)
- `TimestampMixin` — `created_at` / `updated_at`, `server_default=func.now()`, `onupdate=func.now()` on `updated_at`; DB-side timestamps, never Python `utcnow()`
- `SoftDeleteMixin` — `deleted_at: Mapped[datetime | None]`, column only; repos filter `deleted_at IS NULL` (User, Place use it; Trip, Destination, etc. do not)
- SQLAlchemy 2.0 `Mapped[]` + `mapped_column()` throughout — no legacy `Column()` API, no `relationship()` in this file

#### Async session + pool — step 1.2

Module: `src/core/database/session.py`

- **Lazy singleton engine:** `get_engine()` creates on first use; `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=3600`, `echo=settings.DEBUG`
- **Lazy session factory:** `get_session_factory()` → `async_sessionmaker` with `expire_on_commit=False`, `autocommit=False`, `autoflush=False`
- **FastAPI dependency:** `get_db()` yields one `AsyncSession` per request; rolls back on exception before re-raise; closes in `finally`
- **Back-compat alias:** `AsyncSessionLocal()` — callable returning a new session context manager (scripts/smoke tests)
- **Lifecycle:** `ping_db()` — `SELECT 1` via `get_engine().connect()`; `dispose_engine()` — disposes pool and resets `_engine` + `_session_factory` to `None`
- **Connection test script:** `scripts/test_db_conn.py` — standalone (not pytest); prints Postgres version, database name, active connections

```bash
docker compose up -d
python scripts/test_db_conn.py
# Expected: Connected: PostgreSQL 16.x ..., Database: wandr, Pool OK — connection test passed
```

## Build Progress

| Step | Status | Deliverable |
|------|--------|-------------|
| 0.1 | Done | Directory skeleton, `AGENT.md` |
| 0.2 | Done | `src/config.py`, `.env.example` |
| 0.3 | Done | `docker-compose.yml` (PostGIS + Qdrant) |
| 0.4 | Done | `structlog` logging |
| 0.5 | Done | Langfuse tracing + `NoOpTracer` |
| 0.6 | Done | LiteLLM gateway (`chat_completion`, `chat_with_tools`) |
| 0.7 | Done | Pagination (`PageParams`, `PaginatedResponse[T]`, `paginate`) |
| 0.8 | Done | Response envelopes (`ApiResponse[T]`, `ErrorResponse`) |
| 0.9 | Done | Exception hierarchy (`WandrError` tree) |
| 0.10 | Done | FastAPI app factory, lifespan, `/api/v1/health`, global exception handlers |
| 1.1 | Done | `Base`, `UUIDMixin`, `TimestampMixin`, `SoftDeleteMixin` |
| 1.2 | Done | Async engine pool, `get_db()`, `scripts/test_db_conn.py` |
| 1.3+ | Pending | Alembic, models, auth, planner |

## P0 Complete — Verification

Run before starting P1. On Windows, use PowerShell equivalents where noted.

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Directory tree | `find src/ -type d \| sort` | All domain packages present |
| 2 | Guardrails | `head AGENT.md` | Readable at repo root |
| 3 | Settings | `python -c "from src.config import get_settings; print(get_settings().PLANNER_MAX_TOOL_CALLS)"` | `12` |
| 4 | Logging | `configure_logging(); get_logger().info('check', step='p0')` | Structured log line |
| 5 | Tracing | `get_tracer().trace('p0_check')` | `NoOpTracer` or `Langfuse`, no crash |
| 6 | LLM gateway | `from src.core.llm.client import chat_completion, chat_with_tools` | Imports cleanly |
| 7 | litellm isolation | `grep -r "import litellm" src/ \| grep -v client.py` | Zero results |
| 8 | Pagination | `from src.core.pagination import PaginatedResponse, paginate` | OK |
| 9 | Responses | `from src.core.responses import ApiResponse, ErrorResponse` | OK |
| 10 | Exceptions | `from src.core.exceptions import WandrError, NotFoundError, WandrLLMError` | OK |
| 11 | Health | `GET /api/v1/health` | `{"success": true, "data": {"status": "ok", ...}}` |
| 12 | Docker | `docker compose ps` | `wandr_postgres` healthy, `wandr_qdrant` running |

**Run the app** (requires `.env` with `SECRET_KEY`, `DATABASE_URL`, `LLM_API_KEY`, `NOMINATIM_USER_AGENT`):

```bash
docker compose up -d
uvicorn src.main:app --reload
# Health: curl -s http://localhost:8000/api/v1/health | python -m json.tool
```

Local dev notes:
- Postgres: `DATABASE_URL=postgresql+asyncpg://wandr:wandr@localhost:5433/wandr` (port 5433, not 5432)
- Qdrant: `QDRANT_URL=http://localhost:6335` (port 6335 if 6333 is taken by another service)
- No `X-Request-ID` header yet (step 1.8)

## Key Constraints for AI Agents

When implementing any step, always:

1. Read `AGENT.md` first
2. Route all env access through `get_settings()`
3. Keep Router → Service → Repository layering
4. Put external calls behind gateway modules with timeouts, retry, and fallback
5. Record evaluation data on every planner generation
6. Append new packages to `requirements.txt` with a comment
