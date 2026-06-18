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
| `wandr_postgres` | `postgis/postgis:16-3.4` | 5432 | PostgreSQL + PostGIS |
| `wandr_qdrant` | `qdrant/qdrant:latest` | 6333/6334 | Vector search |

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
| 0.8+ | Pending | FastAPI app, DB, auth, planner |

## Key Constraints for AI Agents

When implementing any step, always:

1. Read `AGENT.md` first
2. Route all env access through `get_settings()`
3. Keep Router → Service → Repository layering
4. Put external calls behind gateway modules with timeouts, retry, and fallback
5. Record evaluation data on every planner generation
6. Append new packages to `requirements.txt` with a comment
