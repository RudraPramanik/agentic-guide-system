## Why

P5 delivered the phase-gated tool-loop agent and a service-level `PlannerService.generate` bridge (emit + `wait_for`), but there is still no HTTP SSE surface, trip persistence, guest ownership, Redis-backed rate limit/cache, or pre-graph absolute-min-places floor. `docs/steps/step6.md` is empty while `docs/blueprint_final.md` v6.1 already locks P6 (6.1–6.5). Without a step5-style Cursor build contract, implementers will re-open either/or on SSE queue design, guest 403 rules, transaction boundaries, and Redis vs in-memory backends — and risk coupling routers to concrete Redis/OSRM/LLM clients instead of swappable abstractions.

## What Changes

- Author **`docs/steps/step6.md`** as the hardened P6 Cursor prompt (same shape as `step5.md` / `step4.md`): prerequisites, architecture, locked decisions, ordered sub-steps **6.1–6.5**, each with TASK / FAILURE BOUNDARY / ✅ validation where code lands.
- Align this change’s design/specs/tasks to **`docs/blueprint_final.md` v6.1** Planner SoT (P6 phase + Resilience Contracts + AGENT.md) with explicit emphasis on **fallback**, **scalability**, **abstraction/DI**, and **easy provider swaps** (cache, rate limiter, routing already protocol-based).
- Lock P6 contracts in the prompt: `TripService.save_from_state` Unit of Work, guest `wandr_session` ownership, `POST /planner/generate` StreamingResponse + disconnect cancel + queue, `PLANNER_ABSOLUTE_MIN_PLACES` pre-graph floor, trips CRUD + GeoJSON, `CacheBackend` / Redis `RateLimiterBackend` when `REDIS_URL` set, backend ship checklist.
- Encode **batched OpenSpec implementation clusters** (not one ceremony per micro-step).
- **Non-goals for this design change’s apply:** no production trips/planner HTTP/Redis code until a follow-on apply from the prompt. Primary deliverable is the prompt + OpenSpec alignment.

## Capabilities

### New Capabilities

- `p6-planner-api-persistence`: Contract for the P6 Planner API + Persistence phase — trips repository/service (`save_from_state`, guest ownership, Unit of Work), planner HTTP SSE generate (queue + disconnect cancel + absolute min-places floor), trips CRUD + GeoJSON, Redis-swappable rate limiter + planner result cache, pytest/smoke + backend ship checklist — as specified in the hardened `docs/steps/step6.md` prompt.

### Modified Capabilities

- `rate-limit-middleware`: When `REDIS_URL` is set, select a Redis-backed `RateLimiterBackend` via the existing Protocol factory; empty `REDIS_URL` keeps `InMemoryRateLimiter`. Fail-open unchanged.
- `planner-service-sse-bridge`: HTTP layer consumes the existing `on_event` / emit bridge; service remains the generation runner. Prompt locks how the router adapts it (background task + `asyncio.Queue`) without embedding FastAPI types inside the service.

## Impact

- **Docs:** `docs/steps/step6.md` becomes the sole P6 implementation prompt. Blueprint remains architecture SoT, not the Cursor prompt.
- **Code (once implemented from the prompt):** `src/trips/{repository,service,schemas,router,exceptions}.py` (today stubs except models), `src/planner/{router,schemas}.py` (stubs), Redis-optional backends under `src/core/` (rate limit + cache), `PLANNER_ABSOLUTE_MIN_PLACES` in `get_settings()`, register routers in `main.py`; optional `redis` package only if required with why-comment.
- **AGENT.md:** Router → Service → Repository; SSE wrapped in generation timeout; evaluation never skipped; LLM/geo only via gateways; endpoints return `ApiResponse` / `PaginatedResponse`; all env via `get_settings()`.
- **Abstractions (prompt-locked):** `RateLimiterBackend`, `CacheBackend` (in-memory ↔ Redis), keep `RoutingProvider` / LLM gateway / geo gateways — swap providers via settings, not call-site rewrites.
- **Tests:** trips ownership/UoW; SSE timeout/disconnect; cache hit; rate-limit 429; GeoJSON shape; import guards.
- **Process:** propose → apply (write step6.md) → archive this design change; then implement P6 from the prompt in **batched** OpenSpec applies (e..g. 6.1, 6.2, 6.3, 6.4–6.5).
- **Prerequisites:** P5 complete (5.1–5.14) — especially real `PlannerService.generate` + compiled graph. Context today may still show P5.12 next until 5.12–5.14 ship; do not start P6 code until P5 ship criteria pass.
- **Non-goals:** P7 edit/replan endpoints; sustained daily LLM spend caps; multi-region Redis clustering; turning blueprint into a Cursor prompt wholesale.
