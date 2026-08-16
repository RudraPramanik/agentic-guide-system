## 1. Reproduce and diagnose

- [x] 1.1 Bring up local API (`docker compose up --build`) and confirm `/api/v1/health`; match FE `NEXT_PUBLIC_API_URL` host (`127.0.0.1` vs `localhost`).
- [x] 1.2 Confirm destination under test (e.g. `458854b1-…`) has `place_count >= PLANNER_ABSOLUTE_MIN_PLACES` and note readiness tier.
- [x] 1.3 Capture one cold `POST /api/v1/planner/generate` SSE transcript: event names, terminal code, wall time, last tool/phase from logs; record whether `itinerary_done` is absent on success paths.

## 2. Terminal emit bridge (service)

- [x] 2.1 Add a pure helper that maps final `TravelState` → exactly one terminal (`itinerary_done` | `clarification_needed` | `error`) with locked precedence; unit-test precedence (timeout error already emitted → no second terminal; clarification; success; abort).
- [x] 2.2 Call the helper from `PlannerService.generate` after `ainvoke` return and after timeout/recursion final-state build (skip when timeout/recursion already emitted `error`).
- [x] 2.3 Ensure success `itinerary_done` payload includes itinerary/days fields the router can enrich; clarification payload includes a question string.

## 3. Progress emits (cold path)

- [x] 3.1 Emit `preferences_done` from `parse_preferences` via configurable `emit` (with state snapshot when available).
- [x] 3.2 Emit `phase_changed` when `agent_phase` transitions (tool executor / transition helper); keep FastAPI out of service/nodes.

## 4. Router safety net + tests

- [x] 4.1 If the generate background task completes with no buffered terminal, yield a single terminal `error` (stable code); never hang on progress-only close.
- [x] 4.2 Extend `tests/planner/` so cold-path `generate` (mocked graph or controlled state) asserts exactly one terminal and that success emits `itinerary_done` without `_replay_cached`.
- [x] 4.3 Extend SSE router tests: buffered `itinerary_done` → `save_from_state` + `trip_id`; clarification/error → no trip; missing-terminal safety net fires.

## 5. Timeout reliability (measure then fix)

- [x] 5.1 From 1.3 measurements, identify dominant cost (LLM rounds, stuck loops, OSRM, etc.).
- [x] 5.2 Apply the smallest justified fix (stuck/loop waste, redundant LLM, or documented modest `PLANNER_GENERATION_TIMEOUT_SECONDS` bump only if cold path is just over budget with healthy LLM).
- [x] 5.3 Re-run cold generate: prefer `itinerary_done` + `trip_id` under ceiling; if still timeout, document remaining API bottleneck (do not “fix” via FE abort).

## 6. Docs and ship handoff

- [x] 6.1 Update `docs/FE_guide.md` only if terminal payload keys/codes changed.
- [x] 6.2 Update `docs/context.md` (Last updated, known limitations / live generate note) after proof passes.
- [x] 6.3 Point sibling FE companion change at this change: guest generate → navigate `/trips/{trip_id}`; update `guideagent-frontend/docs/issues/issue.md` status after FE verify.
