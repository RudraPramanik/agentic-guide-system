## Context

**Current state (2026-07-18):** P0 complete. P1 ~80% — SQLAlchemy base/session, Alembic 001–002, six core models, `BaseRepository`, JWT + Google OAuth auth, request-logging middleware, partial pytest harness. Live: `/api/v1/health`, `/api/v1/auth/*`. Stubs remain for geo, search, places/trips/destinations services, planner, travel_engine, rate_limit.

**Next immediate step:** 1.9 — `TripEditEvent` model + migration 003 (`docs/steps/step1.md`).

**Blueprint authority:** `docs/blueprint_final.md` — ~29 dev-days, P0–P7, backend only (frontend map is separate).

## Goals / Non-Goals

**Goals:**

- Finish P1, then execute P2→P7 in order — each phase ends with a runnable proof command.
- Document env/infra needed at each phase so local dev works before prod hosting decisions.
- Describe the **end product**: a production-grade AI travel planner API that generates multi-day itineraries via SSE, persists trips, supports edits, and records evaluation quality signals.

**Non-Goals:**

- Frontend / map UI implementation.
- Full OpenSpec backfill of every blueprint line into `openspec/specs/`.
- Implementing all phases in one apply session — roadmap is sequential; each step gets its own focused change.

## Decisions

### D1 — Strict phase ordering (P1 → P7)

**Decision:** No skipping phases. P5 (agent) requires P2–P4 (geo data, search, travel_engine). P6 (API) requires P5. P7 requires P6 + TripEditEvent (1.9).

**Rationale:** Blueprint dependency graph; building planner before seeded places produces empty itineraries.

### D2 — Local-first, env-swap for prod

**Decision:** Same code paths locally and in prod; swap env vars only (blueprint principle #4).

| Concern | Local (now) | Production (later) |
|---------|-------------|-------------------|
| Postgres + PostGIS | Docker `:5433` | Neon / Supabase / Railway |
| Qdrant | Docker `:6335` | Qdrant Cloud + `QDRANT_API_KEY` |
| Redis (cache + rate limit) | Empty → in-memory | Upstash `REDIS_URL` |
| LLM | `LLM_API_KEY` + `LLM_MODEL` | Same — swap model string only |
| OSRM routing | Public `router.project-osrm.org` | Self-hosted OSRM or Valhalla |
| Geocoding | Nominatim (rate-limited) | Same API, proper User-Agent |
| Observability | Console structlog | JSON logs → Logtail/Datadog; optional Langfuse |

### D3 — What you must provide (by phase)

| Phase | Required from you | Optional / degrades gracefully |
|-------|-------------------|----------------------------------|
| **P1 finish** | `DATABASE_URL`, `SECRET_KEY`, Google OAuth creds for auth | Redis |
| **P2** | `NOMINATIM_USER_AGENT` (real contact email) | — |
| **P3** | `QDRANT_URL` (local Docker) | `QDRANT_API_KEY` (prod only); ~80MB embedding model download on first run |
| **P4** | `OSRM_BASE_URL` (public default works) | — |
| **P5–P6** | **`LLM_API_KEY`** (Groq/NVIDIA NIM/OpenAI via LiteLLM) | Langfuse keys for trace URLs |
| **P6 prod** | Hosted Postgres URL, rate-limit Redis | Planner cache Redis |
| **P7** | Same as P6 | — |

**Minimum to generate a real itinerary (P6 ship checklist):** Docker Postgres + Qdrant, seeded destination (e.g. Darjeeling via `scripts/seed_destination.py`), enrich + index scripts run, valid `LLM_API_KEY`.

### D4 — End product (if blueprint followed completely)

A **FastAPI modular monolith** exposing:

1. **Auth** — Google OAuth, JWT cookie/Bearer, guest sessions.
2. **Destinations** — Search (DB + Nominatim cache-aside), readiness score/tier.
3. **Places** — Paginated POI list, semantic search (Qdrant + PostGIS fallback).
4. **Planner** — `POST /api/v1/planner/generate` SSE stream: phase-gated tool-loop agent produces 1–N day itinerary with ordered stops, `suggested_start_time`, polylines, day narratives. Bounded by `PLANNER_MAX_TOOL_CALLS` and 45s timeout.
5. **Trips** — CRUD, GeoJSON export, anonymous→logged-in claim.
6. **Edit & replan (P7)** — Reorder/remove/add/reoptimize day stops; `TripEditEvent` audit + evaluation linkage.
7. **Evaluation** — Every generation and edit persisted for quality analysis (`tool_trace`, readiness, fallbacks, abort signals).

**Not included:** Web UI, payment, multi-region deployment runbooks (code is prod-ready via env swap).

### D5 — Agent architecture (P5)

**Decision:** Phase-gated tool loop (v5.1 blueprint) — not per-node pipeline.

- Structure (order, times, coords) from `travel_engine/` + tools only.
- LLM chooses tools within phase allowlist; narrative in fixed `write_narrative` node outside loop.
- All external failures → named fallbacks per Resilience Contracts table — never raw 500.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Nominatim 1 req/sec rate limit slows seeding | LRU cache; DB cache-aside for destinations |
| Public OSRM unreliable | Haversine × 1.4 fallback; itinerary still valid |
| Qdrant/embedding model unavailable | `search_available=False`; PostGIS radius fallback |
| LLM rate limits during agent loop | tenacity + Retry-After; default tool chain; partial itinerary on abort |
| Large P5 scope (14 steps) | Implement tools 5.1–5.3 before graph 5.4–5.11 |
| sentence-transformers download/size | Graceful degrade; document first-run download |

## Migration Plan

1. Complete P1 steps 1.9 → 1.10 → 1.12 (update `docs/context.md` after each).
2. Create per-step OpenSpec changes (e.g. `step-1-9-trip-edit-event`, `p2-geo-foundation`) — do not implement entire roadmap in one PR.
3. Run `alembic upgrade head` as deploy step only — never at app startup.
4. Prod: provision Postgres → run migrations → set env → deploy uvicorn → run seed/enrich/index scripts per destination.

## Open Questions

- **Google OAuth:** Are client ID/secret already configured for local callback URL?
- **LLM provider:** Groq vs NVIDIA NIM vs OpenAI — affects `LLM_MODEL` and `LLM_API_BASE` only.
- **First destination:** Darjeeling is blueprint default — confirm or pick another for seed scripts.
- **Frontend:** Separate blueprint — backend P6 ship checklist is API-complete without UI.
