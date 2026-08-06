# Wandr — AI Agent Context

> **Read this first every session.** Then `AGENT.md` (rules), then the current step in `docs/steps/step*.md` (or blueprint).
> **Planner single source of truth:** `docs/blueprint_final.md` **v6.1** (pre-flight addendum merged; `docs/blueprint.md` is a pointer only).
> **Deployment (MVP):** frontend + API under the same registrable domain; auth cookies stay `SameSite=Lax` (Option A).
> Deep reference: `docs/app/system.md` (architecture), `docs/app/lld.md` (patterns).
> Junior map (layers / files / imports): `docs/app/documentation.md` → `docs/manual/` (refresh on phase end or every 4–5 steps — not every step).
> P2 study guide (engineering + interview Q&A): `docs/app/p2guide.md` · books: `docs/books/p2-references.md`
> Developer playbook (OpenSpec workflow + example prompts): `docs/spec.md`

**Last updated:** 2026-08-06 · **Phase:** post-P7 · **Next step:** operator VPS deploy via `docs/steps/blueprint_production.md`

---

## Current state (one line)

P7 done + production packaging — VPS Docker API; hosted Gemini embeddings (`PLACES_EMBEDDING_BACKEND`); deploy SOP in `blueprint_production.md`.

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
| 2.4 | ✅ Done | `scripts/seed_destination.py` — geocode → Overpass → per-POI upsert (savepoint per POI), sets `place_count`, commits |
| 2.5 | ✅ Done | `geo/osrm` — OSRM driving route + haversine × 1.4 fallback |
| 2.6c | ✅ Done | destinations router search + readiness stub; registered in `main.py` |
| 2.6c′ | ✅ Done | path-table rate limits; destinations/search 20/min/IP |
| 2.7a | ✅ Done | `PlaceOut` + `PlaceService` (mandatory destination existence → 404) |
| 2.7b | ✅ Done | places router list/get; registered in `main.py` |
| 2.8 | ✅ Done | pure `compute_readiness` + real `DestinationService.get_readiness` |
| 2.9 | ✅ Done | P2 pytest: geo/readiness/repos/routers/seed (68 tests total) |
| 2.10 | ✅ Done | `scripts/test_p2_smoke.py` live P2 proof |
| 3.0 | ✅ Done | Migration `places.enriched_tags` JSONB list (distinct from OSM `tags`) |
| 3.1 | ✅ Done | `search/client.py` AsyncQdrantClient + fail-soft `ensure_places_collection` |
| 3.2 | ✅ Done | `search/embeddings.py` lifespan MiniLM load + `to_thread` encode |
| 3.3 | ✅ Done | `PlaceService.enrich_place` + `PLACE_TAG_VOCAB` constants |
| 3.4 | ✅ Done | `search/places_index.py` batch upsert + destination-scoped search |
| 3.5 | ✅ Done | `scripts/enrich_places.py` + `scripts/index_places.py` |
| 3.6 | ✅ Done | Readiness uses live `is_qdrant_available()` |
| 4.0 | ✅ Done | CORS middleware + `CORS_ALLOWED_ORIGINS` |
| 4.1 | ✅ Done | `travel_engine/protocols.py` — `RouteLeg`, `RoutingProvider`, `legs_to_lookup` |
| 4.2 | ✅ Done | `travel_engine/travel_rules.py` — structural vs interest vocab + `visit_duration_min` |
| 4.3 | ✅ Done | `travel_engine/place_selector.py` — sum scoring, AVOID_SAME_DAY filter, explain |
| 4.4 | ✅ Done | `travel_engine/day_allocator.py` — cluster-first pack under caps + visit budget |
| 4.5 | ✅ Done | `travel_engine/route_optimizer.py` — matrix-once + permutations + drop-retry `dropped_stops` |
| 4.6 | ✅ Done | `travel_engine/schedule_builder.py` — naive HH:MM, lunch gap, morning-only slots |
| 4.7 | ✅ Done | `travel_engine/trip_validator.py` — CoR checks + dropped_stops warning |
| 4.8 | ✅ Done | `OsrmRoutingProvider` + `ToolResult` / `execute_tool` skeleton |
| 4.9 | ✅ Done | P4 pytest: travel_engine + purity + CORS + planner adapter/envelope |
| 4.10 | ✅ Done | `scripts/test_p4_smoke.py` offline Fake pipeline (+ optional live OSRM) |
| 5.1 | ✅ Done | `AgentPhase` / `PHASE_TOOLS` / `ToolContext` + 12-tool `TOOL_REGISTRY` + phase-gated `execute_tool` |
| 5.2 | ✅ Done | DISCOVER tools: `check_readiness`, `search_places`, `rank_places` |
| 5.3 | ✅ Done | PLAN/VALIDATE/control/REPLAN tools (9) + `finish_plan` precondition |
| 5.4 | ✅ Done | Verify `chat_with_tools` + `tests/core/test_llm_chat_with_tools.py` |
| 5.5 | ✅ Done | `apply_tool_result` / `maybe_transition_phase` / `check_preconditions` + tool_trace bookkeeping |
| 5.6 | ✅ Done | `TravelState` TypedDict + `langgraph==0.2.76` (hello-world configurable passthrough) |
| 5.7 | ✅ Done | `build_agent_messages` — phase-aware system prompt + REPLAN expand guidance |
| 5.8 | ✅ Done | `parse_preferences` — `chat_completion` JSON bookend; defaults on LLM fail |
| 5.9 | ✅ Done | `agent_node` + `tool_executor_node` — sole `execute_tool` + stuck-detector |
| 5.10 | ✅ Done | `write_narrative` + `record_evaluation` + evaluation repo/service |
| 5.11 | ✅ Done | `build_planner_graph` / `get_compiled_graph` singleton compile |
| 5.12 | ✅ Done | `PlannerService.generate` — emit bridge, `wait_for`, settings-derived `recursion_limit` |
| 5.13 | ✅ Done | `tests/planner/test_tool_loop.py` — ★ cases incl. stuck/timeout/concurrent ctx (162 suite) |
| 5.14 | ✅ Done | `scripts/test_agent.py` live smoke sections 1–8 PASS (provider via `LLM_*` env; not vendor-locked) |
| 6.0 | ✅ Done | `route_polyline` + OptimizeResult polylines; schedule day-dict shape with `leg_polyline`/`day_polyline` |
| 6.1 | ✅ Done | trips exceptions/schemas/repo/service — `save_from_state` UoW, ownership, `claim_for_user` |
| 6.2 | ✅ Done | planner schemas + SSE `/generate` — floor 409, terminal buffer + save, proxy headers |
| 6.3 | ✅ Done | trips HTTP CRUD + GeoJSON + claim (`build_geojson`, ownership 403, claim 200/403/409) |
| 6.4 | ✅ Done | `CacheBackend` + Redis/InMemory rate limiter; planner MVP cache hit still persists new trip |
| 6.5 | ✅ Done | P6 pytest gaps + `scripts/test_p6_smoke.py` + import guards; Next → P7.1 |
| 7.0 | ✅ Done | `save_from_state` base prefs + `_resolve_base` (prefs → Destination); no migration |
| 7.1 | ✅ Done | Public `populate_leg_polylines`; `optimize_route` calls it; legs stay full pairwise |
| 7.2 | ✅ Done | TripService edit ops + preserve-order schedule; TripEditEvent UoW; thin `mark_trip_edited` |
| 7.3 | ✅ Done | trips edit HTTP (4 routes) + `rate_limit_trip_edit` + `RateLimitedError` 429 |
| 7.4 | ✅ Done | `tests/trips/test_edit_replan.py` — 20 locked scenarios + persist SQL-delete fix |
| 7.5 | ✅ Done | `EvaluationService.mark_trip_edited` flag polish — `get_latest_for_trip` + `mark_user_edited(evaluation)` |
| 7.6 | ✅ Done | P7 smoke (`scripts/test_p7_smoke.py`) + import guards; context P7-complete stamp |
---

## Implemented modules (real code)

| Module | Exports / notes |
|--------|-----------------|
| `src/config.py` | `get_settings()` — Qdrant/embeddings (`PLACES_EMBEDDING_BACKEND`, `GEMINI_API_KEY`), enrich concurrency, OAuth, JWT, rate limits (incl. `RATE_LIMIT_TRIP_EDIT_*`), geo, CORS, `PLANNER_ABSOLUTE_MIN_PLACES`, `PLANNER_CACHE_TTL_SECONDS`, `REDIS_URL` + Redis timeouts |
| `src/core/llm/client.py` | `chat_completion` / `chat_with_tools` / `embed_texts` — **only** litellm import |
| `src/search/embeddings.py` | `local` MiniLM or `hosted` via `embed_texts`; fail-soft; lazy ST import |
| `src/core/cache/backends.py` | `CacheBackend` Protocol; `InMemoryCacheBackend` / `RedisCacheBackend`; `get_cache_backend()` |
| `src/core/middleware/rate_limit.py` | `InMemoryRateLimiter` / `RedisRateLimiter`; `get_rate_limiter()` selects on `REDIS_URL`; fail-open |
| `src/planner/schemas.py` | `PlanRequest` (destination_id, raw_input, optional days/base/accommodation_label) |
| `src/planner/cache.py` | MVP key + `maybe_get_cached_state` / `maybe_set_cached_state` / `_replay_cached` (skip tool loop; still feeds `save_from_state`) |
| `src/planner/router.py` | `POST /generate` SSE — floor check, queue+task, terminal buffer → `save_from_state` + `trip_id`, cache set on fresh success, proxy headers |
| `src/destinations/exceptions.py` | + `DestinationNotReadyError` (409 `destination_not_ready`) |
| `src/travel_engine/protocols.py` | `RouteLeg`, `RoutingProvider` (`travel_matrix` + `route_polyline`), `legs_to_lookup` — pure, no I/O |
| `src/travel_engine/travel_rules.py` | Caps, structural durations, interest weights, `visit_duration_min` |
| `src/travel_engine/place_selector.py` | `PlaceCandidate`, `TripPreferences`, `ScoredPlace`, `score_place`, `select_places`, `explain_selection` |
| `src/travel_engine/day_allocator.py` | `allocate_days` — cluster + caps/budget + morning≤2/day + soft geo spill |
| `src/travel_engine/route_optimizer.py` | `optimize_route` — full-matrix legs; drop until under travel or 1 stop; public `populate_leg_polylines` for winning/fixed order |
| `src/travel_engine/schedule_builder.py` | `build_day_schedule` — morning extract ≤2; `preserve_order=True` skips extract (P7 reorder) |
| `src/travel_engine/trip_validator.py` | `validate_trip`, `ValidationResult`, `DayPlan`, `TripItinerary` — pure CoR rules; morning errors prefixed `morning_slot_violation:` |
| `src/planner/routing_provider.py` | `OsrmRoutingProvider` — `travel_matrix` + fail-soft `route_polyline` via `geo/osrm.get_route` |
| `src/planner/tools/schemas.py` | `AgentPhase`, `PHASE_TOOLS`, `ToolResult` (+`fallback_used`), `ToolContext`, 12 input models |
| `src/planner/tools/registry.py` | 12-tool `TOOL_REGISTRY`, phase/precondition `execute_tool`, re-exports orchestration helpers |
| `src/planner/tools/orchestration.py` | `check_preconditions`, `apply_tool_result` (sole writer), `maybe_transition_phase`, `_make_test_state` |
| `src/planner/tools/constants.py` | `RANK_EXPLANATION_TOP_N`, `SEARCH_EXPAND_FACTOR`, search defaults |
| `src/planner/tools/*.py` (12) | Real tool bodies → `ToolResult` only (no TravelState mutation) |
| `src/planner/graph/state.py` | `TravelState` TypedDict — no db/routing; schedule = day-dict list (P6.0); list fields last-write-wins |
| `src/planner/graph/messages.py` | `build_agent_messages` — phase + PHASE_TOOLS + compact summary |
| `src/planner/graph/nodes/parse_preferences.py` | Fixed `chat_completion` prefs bookend; defaults + `llm_retry_count` on fail |
| `src/planner/graph/nodes/agent.py` | Decides `pending_tool_calls` only (nudge / phase-default); never runs tools |
| `src/planner/graph/nodes/tool_executor.py` | Sole `execute_tool` caller; `apply_tool_result` + stuck-detector every cycle |
| `src/planner/graph/nodes/write_narrative.py` | Titles/paragraphs via `chat_completion`; templates on LLM fail; geometry locked |
| `src/planner/graph/nodes/record_evaluation.py` | Best-effort `EvaluationService.record_generation`; warning on DB fail |
| `src/planner/graph/builder.py` | Compiled graph singleton — agent→executor unconditional; bookends on `plan_complete` |
| `src/planner/service.py` | `PlannerService.generate` — fresh ToolContext, emit/`last_known_state`, `wait_for`, recursion ceiling |
| `src/evaluation/repository.py` | `EvaluationRepository` — flush-only create; `get_latest_for_trip`; `mark_user_edited(evaluation)` |
| `src/evaluation/service.py` | `record_generation(state)` + `mark_trip_edited` flag-only (no TripEditEvent; skip if missing/already flagged) |
| `src/planner/tools/schemas.py` | + `DEFAULT_TOOL_BY_PHASE` (nudge / LLM-fail defaults) |
| `src/planner/tools/registry.py` | + `parse_tool_input`; re-exports `run_stuck_detector` |
| `src/planner/tools/orchestration.py` | + unconditional `run_stuck_detector` |
| `src/core/observability/logging.py` | `configure_logging()`, `get_logger()` |
| `src/core/observability/tracing.py` | `get_tracer()`, `flush_tracer()` |
| `src/core/llm/client.py` | (see Implemented modules — includes hosted `embed_texts`) |
| `src/core/pagination.py` | `PageParams`, `PaginatedResponse[T]`, `paginate()` |
| `src/core/responses.py` | `ApiResponse[T]`, `ErrorResponse` |
| `src/core/exceptions.py` | `WandrError` tree + `RateLimitedError` (429 `rate_limit_exceeded`) |
| `src/core/database/base.py` | `Base`, mixins (SQLAlchemy 2.0 `Mapped[]`) |
| `src/core/database/session.py` | `get_engine()`, `get_session_factory()`, `get_db()`, `ping_db()`, `dispose_engine()` |
| `src/core/database/base_repository.py` | `BaseRepository[ModelT, IDT]` — soft-delete, paginate, flush-only writes |
| `src/core/security/jwt.py` | `TokenPayload`, `create_access_token()`, `verify_token()` |
| `src/core/security/permissions.py` | `require_auth`, `optional_auth`, `get_current_user_id` |
| `src/core/middleware/logging.py` | `RequestLoggingMiddleware` |
| `src/core/middleware/rate_limit.py` | `RateLimitMiddleware`, path limits, Redis/InMemory backends |
| `src/main.py` | lifespan: DB ping + Qdrant ensure + embedding load; CORSMiddleware; routers |
| `alembic/env.py` | Async Alembic + model imports |
| `alembic/versions/001_enable_postgis.py` | PostGIS + uuid-ossp |
| `alembic/versions/20260717_*_create_all_tables.py` | Migration 002 — 6 core tables |
| `alembic/versions/20260721_*_add_trip_edit_events.py` | Migration 003 — `trip_edit_events` |
| `alembic/versions/20260728_*_add_place_enriched_tags.py` | Migration 004 — `places.enriched_tags` |
| `src/auth/*` | User model, OAuth service, JWT auth router |
| `src/destinations/*` | search + readiness (`is_qdrant_available` live) |
| `src/places/models.py` | `tags` (OSM) + `enriched_tags` (LLM list) + POINT |
| `src/places/constants.py` | `PLACE_TAG_VOCAB` |
| `src/places/service.py` | list/get + `enrich_place` |
| `src/places/repository.py` / `router.py` / `schemas.py` | P2 places HTTP |
| `src/search/client.py` | `AsyncQdrantClient`, `ensure_places_collection`, `is_qdrant_available` |
| `src/search/embeddings.py` | (see above — local MiniLM or hosted `embed_texts`) |
| `src/search/places_index.py` | upsert, `search_places`, `count_indexed` |
| `src/geo/*` | geocoder, overpass, osrm |
| `src/trips/models.py` | Trip / TripPlace / TripEditEvent (+ `Trip.places` / `TripPlace.place` relationships for eager load) |
| `src/trips/exceptions.py` | `TripNotFoundError`, `TripForbiddenError`, `TripAlreadyClaimedError` (409), `TripEditValidationError` (422), `TripStopConflictError` (409), `TripStopNotFoundError` (404) |
| `src/trips/schemas.py` | `TripOut` / `TripPlaceOut`; `ReorderStopsIn` / `AddStopIn` |
| `src/trips/repository.py` | `TripRepository` — list/get_with_places, flush-only place insert/delete, sole `insert_edit_event` |
| `src/trips/service.py` | `save_from_state` UoW; `_resolve_base`; ownership/claim/GeoJSON; day surgery `reorder_stops` / `remove_stop` / `add_stop` / `reoptimize_day` (RoutingProvider DI; no PlannerService); TripEditEvent + `mark_trip_edited` in same UoW; persist uses SQL `delete_trip_place` (avoids cascade resurrect) |
| `src/trips/polyline.py` | Pure Google-encoded polyline decode (no package; invalid → `[]`) |
| `src/trips/dependencies.py` | `rate_limit_trip_edit` — user-keyed `{user_id}:trip_edit`; fail-open; dual OK with middleware IP |
| `src/trips/router.py` | CRUD + GeoJSON + claim + four day-edit routes (`require_auth` via rate-limit dep); DELETE require_auth intentional vs guest GET |
| `src/evaluation/models.py` | TripEvaluation |

**Tests:** `tests/core/`, `tests/auth/`, `tests/geo/`, `tests/destinations/`, `tests/places/`, `tests/search/`, `tests/scripts/`, `tests/travel_engine/`, `tests/planner/`, `tests/trips/`, `tests/evaluation/` — run `python -m pytest tests/ -v` (DB `wandr_test`) — **248** when DB up (incl. `test_mark_trip_edited` flag scenarios, `test_edit_replan` 20-scenario matrix, trip edit HTTP auth/429, Fake ops, preserve-order schedule, cache backends, Redis limiter fail-open, SSE cache-hit new trip_id, trips CRUD)

**Scripts:** `scripts/test_db_conn.py`, `scripts/test_p1_smoke.py`, `scripts/test_p2_smoke.py`, `scripts/test_p4_smoke.py`, `scripts/test_agent.py`, `scripts/test_p6_smoke.py`, `scripts/test_p7_smoke.py`, `scripts/test_geocoder.py`, `scripts/test_overpass.py`, `scripts/seed_destination.py`, `scripts/enrich_places.py`, `scripts/index_places.py`

**Known limitations / TODO (post-P7):** geocoder cache + Nominatim throttle are per-process; empty `REDIS_URL` keeps rate limit + planner cache in-memory (not shared across workers) — set `REDIS_URL` for multi-worker prod. Prod uses **hosted** embeddings (`PLACES_EMBEDDING_BACKEND=hosted`, Gemini via LiteLLM) — dim cutover 384→768 requires Qdrant recreate + `index_places` reindex (see `docs/steps/blueprint_production.md`). Local MiniLM remains `BACKEND=local`. **P7 MVP:** concurrent trip edits are last-write-wins (no row locking).

---

## Stubs only (do not assume implemented)

trips HTTP CRUD + GeoJSON/claim **real** (P6.3); planner **HTTP SSE** `/planner/generate` **real** (6.2); planner cache + Redis/in-memory backends **real** (6.4). evaluation HTTP still stub (generation persist + locked flag-only `mark_trip_edited` **real**); `src/auth/dependencies.py` — still step 0.1 placeholders. Planner **tools** + **orchestration** + **graph** + `PlannerService.generate` (5.1–5.14) are **real**. Route geometry (`route_polyline`, schedule polylines) **real** (6.0); shared `populate_leg_polylines` **real** (7.1); TripService day surgery + preserve-order schedule **real** (7.2); trips edit HTTP + user-keyed `rate_limit_trip_edit` **real** (7.3); full edit/replan pytest **real** (7.4); evaluation flag polish **real** (7.5); P7 smoke + context close-out **real** (7.6). Clarification path ends at END without graph `record_evaluation`; service always calls `record_evaluation` after invoke/timeout. Search + enrich/index scripts **real** (P3). `travel_engine/*` through validator **real** (P4). **P7 complete** — do not claim evaluation HTTP done.

**Deployment / frontend notes:** Operator SOP `docs/steps/blueprint_production.md` — VPS API Docker (`Dockerfile`, `docker-compose.prod.yml` api+Caddy); root `docker-compose.yml` is **dev-only**. Proxy MUST not buffer `/api/v1/planner/generate` (Caddy `flush_interval -1` / nginx `proxy_buffering off`). Frontend must use `fetch()` + manual SSE parsing — native `EventSource` is GET-only and cannot POST. After login, retain `wandr_session` cookie to `POST /trips/{id}/claim`. Empty `REDIS_URL` → in-memory rate limit + planner cache. **FE stack + integration contract:** `docs/FE_guide.md` (sibling Next.js repo; env-swappable `NEXT_PUBLIC_API_URL`).

---

## Live endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/health` | None |
| GET | `/api/v1/auth/google` | None (redirect or not-configured message) |
| GET | `/api/v1/auth/callback` | None (OAuth redirect) |
| GET | `/api/v1/auth/me` | Optional (guest or cookie/Bearer) |
| POST | `/api/v1/auth/logout` | None |
| GET | `/api/v1/destinations/search?q=` | None (public catalog; rate limit 20/min/IP) |
| GET | `/api/v1/destinations/{id}/readiness` | None (`search_available` = live Qdrant flag) |
| GET | `/api/v1/places?destination_id=` | None (paginated; unknown destination → 404) |
| GET | `/api/v1/places/{id}` | None |
| POST | `/api/v1/planner/generate` | Optional (SSE; floor 409 if place_count low; `wandr_session` cookie) |
| GET | `/api/v1/trips` | Required |
| GET | `/api/v1/trips/{id}` | Optional + ownership (guest session or owner) |
| GET | `/api/v1/trips/{id}/geojson` | Public FeatureCollection |
| DELETE | `/api/v1/trips/{id}` | Required + ownership (no anonymous delete) |
| POST | `/api/v1/trips/{id}/claim` | Required + session match + unclaimed |
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | Required + owner + `rate_limit_trip_edit` |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | Required + owner + `rate_limit_trip_edit` |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | Required + owner + `rate_limit_trip_edit` |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | Required + owner + `rate_limit_trip_edit` |

---

## Local dev quick ref

```bash
docker compose up -d          # Postgres :5433, Qdrant :6335
uvicorn src.main:app --reload
# or: python -m uvicorn src.main:app --reload --port 8000
# browser: http://localhost:8000/docs  and  /api/v1/destinations/search?q=Darjeeling
python scripts/test_db_conn.py
python scripts/test_p1_smoke.py
python scripts/test_geocoder.py "Darjeeling"   # needs PYTHONPATH=project root if imports fail
python scripts/test_overpass.py 27.041 88.263 30   # public Overpass may 504; override OVERPASS_API_URL if needed
python scripts/seed_destination.py --destination "Darjeeling" --radius 30   # idempotent; exit 1 only on geocode miss
python scripts/enrich_places.py --destination "Darjeeling" --limit 0   # LLM required
python scripts/index_places.py --destination "Darjeeling" --limit 0    # Qdrant + embeddings
python scripts/test_p2_smoke.py   # network + commits seed data to dev DB
python scripts/test_p4_smoke.py   # offline Fake travel_engine pipeline
# OPTIONAL_LIVE_OSRM=1 python scripts/test_p4_smoke.py
python scripts/test_p7_smoke.py   # offline Fake trip reorder + TripEditEvent + GeoJSON
# OPTIONAL_LIVE_OSRM=1 python scripts/test_p7_smoke.py
# alembic: local package named `alembic/` shadows CLI — run via site-packages alembic or path workaround
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
