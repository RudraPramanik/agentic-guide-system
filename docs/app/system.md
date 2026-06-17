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

### Tracing — step 0.5 (planned)

`src/core/observability/tracing.py` — Langfuse with `NoOpTracer` fallback (Null Object Pattern).

## Build Progress

| Step | Status | Deliverable |
|------|--------|-------------|
| 0.1 | Done | Directory skeleton, `AGENT.md` |
| 0.2 | Done | `src/config.py`, `.env.example` |
| 0.3 | Done | `docker-compose.yml` (PostGIS + Qdrant) |
| 0.4 | Done | `structlog` logging |
| 0.5+ | Pending | Tracing, LLM client, FastAPI app, DB, auth, planner |

## Key Constraints for AI Agents

When implementing any step, always:

1. Read `AGENT.md` first
2. Route all env access through `get_settings()`
3. Keep Router → Service → Repository layering
4. Put external calls behind gateway modules with timeouts, retry, and fallback
5. Record evaluation data on every planner generation
6. Append new packages to `requirements.txt` with a comment
