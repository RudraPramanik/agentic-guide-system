## Why

P0 is complete and P1 is ~80% done (auth, models, JWT, logging live; TripEditEvent, rate limit, and P1 smoke test remain). The team needs a single, blueprint-aligned roadmap that states what to build next, what external services and env vars are required at each phase, and what the finished backend delivers — so implementation stays sequential and nothing is built before its dependencies exist.

## What Changes

This change does **not** ship product code in one pass. It defines the execution plan from **step 1.9 through P7** per `docs/blueprint_final.md`:

- **Finish P1** (steps 1.9–1.12): `TripEditEvent` migration 003, rate-limit middleware stub, pytest middleware asserts, P1 DB smoke script.
- **P2 — Geo foundation**: Nominatim geocoder, Overpass POI scraper, OSRM routing, destination/place APIs, seed script, readiness scoring.
- **P3 — Place knowledge**: Qdrant client, sentence-transformers embeddings, LLM place enrichment, semantic search index.
- **P4 — Travel engine**: Pure-Python routing/scheduling/validation (`travel_engine/`) + `OsrmRoutingProvider`.
- **P5 — Planner agent**: Phase-gated LangGraph tool loop (12 tools), SSE event bridge, evaluation recording.
- **P6 — Planner API + trips**: `POST /planner/generate` (SSE), trips CRUD + GeoJSON, rate limit on generate, planner cache.
- **P7 — Edit & replan**: Reorder/remove/add/reoptimize day endpoints + `TripEditEvent` audit trail.

**Non-goals for this roadmap artifact:** frontend/map UI, mobile apps, payment, multi-tenant admin, backfilling every blueprint line into `openspec/specs/` upfront.

## Capabilities

### New Capabilities

Roadmap-level capability specs (requirements contracts for upcoming phases — implement via `/opsx:apply` on each numbered step change, not all at once):

- `trip-edit-event`: `TripEditEvent` model + migration 003; audit row for P7 edits.
- `rate-limit-middleware`: In-memory dev / Redis prod rate limiter on planner routes; fail-open on error.
- `geo-foundation`: Geocoder, Overpass, OSRM gateways; destination search; place CRUD; seed script.
- `destination-readiness`: Pure scoring + `GET /destinations/{id}/readiness`.
- `place-knowledge`: Qdrant collection, embeddings, enrich + index scripts, semantic search with PostGIS fallback.
- `travel-engine`: Pure Python place selection, day allocation, route optimization, schedule builder, trip validator.
- `planner-tool-loop`: Typed tool registry, phase gating, 12 planner tools, LangGraph agent loop.
- `planner-sse-api`: Streaming `POST /planner/generate` with bounded timeout and event sequence.
- `trips-persistence`: Save from agent state, CRUD, GeoJSON export, anonymous session claim.
- `trip-edit-replan`: P7 PATCH/DELETE/POST edit endpoints with validation rollback.

### Modified Capabilities

- `database-migrations`: Add migration 003 (`trip_edit_events` table + index).
- `pytest-harness`: Extend asserts for rate-limit and middleware headers after 1.10.

## Impact

| Area | Impact |
|------|--------|
| **Code** | All stub domains under `src/geo/`, `src/search/`, `src/places/`, `src/destinations/`, `src/trips/`, `src/planner/`, `src/travel_engine/`, `src/evaluation/` become real modules |
| **APIs** | ~15 new endpoints (destinations, places, planner SSE, trips CRUD/edit, readiness) |
| **Packages** | `qdrant-client`, `sentence-transformers`, `langgraph` added at point of use per blueprint |
| **Infra (local)** | Docker Postgres :5433 + Qdrant :6335; optional Redis later |
| **Infra (prod)** | Hosted Postgres (Neon/Supabase), Qdrant Cloud, LLM API key, optional Upstash Redis, self-hosted or public OSRM |
| **Secrets user must provide** | `LLM_API_KEY`, `SECRET_KEY`, Google OAuth (auth), `DATABASE_URL`, optional Langfuse/Qdrant/Redis keys |
