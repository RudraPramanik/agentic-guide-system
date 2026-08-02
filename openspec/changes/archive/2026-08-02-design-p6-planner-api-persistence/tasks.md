## 1. Author hardened `docs/steps/step6.md`

- [x] 1.1 Write header + SoT pointers: blueprint_final v6.1, context.md, AGENT.md; state that blueprint is architecture SoT and step6 is the Cursor build contract; note OpenSpec = batched clusters; **P5 prerequisite gate** (refuse code apply until PlannerService.generate + P5 ship criteria exist)
- [x] 1.2 Add Decision / Fix Log table locking P6 footguns (await-then-dump SSE, guest 403 vs 404, Trip orphan without places, Redis imports in routers, absolute min-places after LLM spend, FastAPI types inside PlannerService, cache key missing base coords, P7 edit endpoints creeping in)
- [x] 1.3 Add Prerequisites (P5 complete), Prompt conventions, FAILURE BOUNDARY / ✅ Failure path standards (match step5)
- [x] 1.4 Add P6 architecture diagram + abstraction/DI map (`RateLimiterBackend`, `CacheBackend`, `RoutingProvider`, LLM gateway) + locked build order `6.1 → … → 6.5` (design D11)
- [x] 1.5 Lock design decisions in-doc: Unit of Work save, guest ownership 403, SSE queue + disconnect cancel, 409 `destination_not_ready`, Protocol backends + REDIS_URL factory, cache-aside key/TTL, auto-save guests, design-pattern map (D1–D10)
- [x] 1.6 Author Step **6.1** — trips repository + `TripService.save_from_state` + ownership helpers + schemas/exceptions — TASK, FAILURE BOUNDARY, ✅ validation
- [x] 1.7 Author Step **6.2** — planner schemas + `POST /planner/generate` StreamingResponse (pre-graph floor, Queue, background generate, optional_auth, default base lat/lng, auto-save hook) — TASK, FAILURE BOUNDARY, ✅ validation
- [x] 1.8 Author Step **6.3** — trips CRUD router + GeoJSON builder — TASK, FAILURE BOUNDARY, ✅ validation
- [x] 1.9 Author Step **6.4** — Redis `RateLimiterBackend` + `CacheBackend` planner cache (in-memory fallback, fail-open / skip-cache) — TASK, FAILURE BOUNDARY, ✅ validation
- [x] 1.10 Author Step **6.5** — backend ship checklist + pytest/API smoke + import guards + `context.md` update rules
- [x] 1.11 Add P6 Complete verification checklist + ship criteria table + Recommended OpenSpec implementation batches (6.1, 6.2, 6.3, 6.4–6.5)
- [x] 1.12 Ensure every code step has TASK body, FAILURE BOUNDARY, and runnable ✅ validation (Windows `Select-String` where grep would appear)

## 2. Align OpenSpec + process notes

- [x] 2.1 Confirm proposal/design/specs match the prompt locks (no FastAPI in service; 409 floor; Protocol backends; guest 403; no P7 edits)
- [x] 2.2 Emphasize in step6.md that implementation OpenSpec applies are **batched** for speed — not one propose→archive per micro-step
- [x] 2.3 Forward-lock only (do not implement in P6): edit/replan HTTP (P7), daily LLM spend caps, multi-region Redis

## 3. Apply gate (this change only)

- [x] 3.1 Verify `docs/steps/step6.md` exists and is non-empty with sections 6.1–6.5 + verification checklist + abstraction/fallback locks
- [x] 3.2 Run `openspec status --change design-p6-planner-api-persistence` and prepare archive after user review
- [x] 3.3 Do **not** mark P6 code complete in `docs/context.md` in this change — context updates land after implementation validations from the prompt; do **not** register `/planner/generate` as live until 6.2 ships
