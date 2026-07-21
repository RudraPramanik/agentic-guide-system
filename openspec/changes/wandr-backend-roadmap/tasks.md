## 1. Finish P1 (immediate — steps 1.9–1.12)

- [ ] 1.1 Implement `TripEditEvent` model in `src/trips/models.py` per blueprint schema
- [ ] 1.2 Create Alembic migration 003 + index on `trip_id`; run `alembic upgrade head`
- [ ] 1.3 Implement rate-limit middleware stub in `src/core/middleware/rate_limit.py` (in-memory dev)
- [ ] 1.4 Register rate-limit middleware in `main.py` middleware chain
- [ ] 1.5 Add pytest asserts for `X-Request-ID` on health/auth (deferred from 1.11)
- [ ] 1.6 Create P1 DB smoke script (`scripts/test_p1_db.py` or extend step1 proof) — PostGIS geometry + soft-delete
- [ ] 1.7 Update `docs/context.md` — P1 complete, next step P2.1

## 2. P2 — Geo foundation (4 days · 8 steps)

- [ ] 2.1 Implement `src/geo/schemas.py`, `geocoder.py` with resilience contract + LRU cache
- [ ] 2.2 Implement `src/geo/overpass.py` POI scraper
- [ ] 2.3 Implement `src/places/repository.py` — upsert, radius, paginated list
- [ ] 2.4 Implement `scripts/seed_destination.py` — geocode → overpass → upsert
- [ ] 2.5 Implement `src/geo/osrm.py` with haversine fallback
- [ ] 2.6 Implement destinations repo/service/router + `GET /destinations/search`
- [ ] 2.7 Implement places service/router — list + get by id
- [ ] 2.8 Implement `destinations/readiness.py` + `GET /destinations/{id}/readiness`
- [ ] 2.9 Seed Darjeeling; verify readiness tier `ready`; update `docs/context.md`

## 3. P3 — Place knowledge (3 days · 5 steps)

- [ ] 3.1 Add `qdrant-client`; implement `src/search/client.py` + lifespan bootstrap
- [ ] 3.2 Add `sentence-transformers`; implement `src/search/embeddings.py`
- [ ] 3.3 Implement `places/service.py` enrich_place via LLM JSON mode
- [ ] 3.4 Implement `src/search/places_index.py` — upsert + semantic search
- [ ] 3.5 Run `scripts/enrich_places.py` + `scripts/index_places.py` for Darjeeling; update `docs/context.md`

## 4. P4 — Travel engine (5 days · 8 steps)

- [ ] 4.1 Implement `travel_engine/protocols.py` — RoutingProvider, RouteLeg
- [ ] 4.2 Implement `travel_engine/travel_rules.py` constants
- [ ] 4.3 Implement `travel_engine/place_selector.py`
- [ ] 4.4 Implement `travel_engine/day_allocator.py`
- [ ] 4.5 Implement `travel_engine/route_optimizer.py` with injectable routing
- [ ] 4.6 Implement `travel_engine/schedule_builder.py`
- [ ] 4.7 Implement `travel_engine/trip_validator.py`
- [ ] 4.8 Implement `planner/routing_provider.py` + tool registry skeleton; unit tests with FakeRoutingProvider; update `docs/context.md`

## 5. P5 — Phase-gated tool loop agent (7 days · 14 steps)

- [ ] 5.1 Implement `planner/tools/schemas.py` + `registry.py` with PHASE_TOOLS
- [ ] 5.2 Implement core DISCOVER tools: check_readiness, search_places, rank_places
- [ ] 5.3 Implement PLAN/VALIDATE/REPLAN/WRAP_UP tools (build_route through accept_partial)
- [ ] 5.4 Verify `chat_with_tools()` in core LLM client (may already exist from P0)
- [ ] 5.5 Complete registry phase gating, preconditions, phase transitions
- [ ] 5.6 Add `langgraph`; implement `planner/graph/state.py` TravelState
- [ ] 5.7 Implement `planner/graph/messages.py` agent prompt builder
- [ ] 5.8 Implement `nodes/parse_preferences.py`
- [ ] 5.9 Implement `nodes/agent.py` + `nodes/tool_executor.py`
- [ ] 5.10 Implement `nodes/write_narrative.py` + `nodes/record_evaluation.py`
- [ ] 5.11 Implement `planner/graph/builder.py` — compile graph
- [ ] 5.12 Implement `planner/service.py` SSE event bridge
- [ ] 5.13 Add `tests/planner/test_tool_loop.py`
- [ ] 5.14 Add `scripts/test_agent.py` end-to-end Darjeeling proof; update `docs/context.md`

## 6. P6 — Planner API + trips persistence (3 days · 5 steps)

- [ ] 6.1 Implement trips repo/service — save_from_state, list, get_with_places
- [ ] 6.2 Implement `planner/router.py` — POST /planner/generate SSE with timeout wrapper
- [ ] 6.3 Implement trips router — CRUD + GeoJSON export
- [ ] 6.4 Wire rate limit on planner generate + planner result cache (Redis optional)
- [ ] 6.5 Run P6 ship checklist from blueprint; `pytest tests/ -v` green; update `docs/context.md`

## 7. P7 — Edit & replan (2 days · 4 steps)

- [ ] 7.1 Implement trips service edit ops — reorder, remove, add, reoptimize_day
- [ ] 7.2 Implement P7 router endpoints with auth + ownership checks
- [ ] 7.3 Add `tests/trips/test_edit_replan.py`
- [ ] 7.4 Wire evaluation `record_edit()` + user_edited flag; update `docs/context.md`

## 8. Production readiness (after P7)

- [ ] 8.1 Provision hosted Postgres; run migrations
- [ ] 8.2 Configure Qdrant Cloud + `QDRANT_API_KEY`
- [ ] 8.3 Set production `LLM_API_KEY`, `SECRET_KEY`, Google OAuth redirect URLs
- [ ] 8.4 Optional: Upstash Redis for rate limit + planner cache
- [ ] 8.5 Optional: Langfuse keys for production tracing
- [ ] 8.6 Seed/enrich/index production destination(s)
