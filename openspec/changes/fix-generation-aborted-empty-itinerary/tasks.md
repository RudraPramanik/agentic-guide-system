## 1. State-aware agent defaults

- [x] 1.1 Add `_default_tool_for_state` in `src/planner/graph/nodes/agent.py` (DISCOVER: check_readiness → search_places → rank_places; PLAN: build_route vs build_schedule) and use it for no-tool and `WandrLLMError` synthesize paths
- [x] 1.2 Add/adjust planner tests so LLM failure after readiness synthesizes `search_places`, and initial empty state still defaults to `check_readiness`

## 2. Stuck detector and build_route

- [x] 2.1 Update `run_stuck_detector` so stuck DISCOVER with empty candidates and stuck PLAN with no usable schedule abort to WRAP_UP instead of auto-advancing
- [x] 2.2 Make `build_route` return `ok=False` / `no_ranked_places` when ranked and candidates are both empty; keep auto-rank from candidates
- [x] 2.3 Add unit tests for empty `build_route` and stuck DISCOVER-without-POIs; run `tests/planner`

## 3. Live proof and docs

- [x] 3.1 With Compose up, POST `/api/v1/planner/generate` for destination `458854b1-4d2a-4d02-8901-e26ed59c0c8b` and confirm SSE `search_places` then `itinerary_done` + `trip_id`
- [x] 3.2 Document symptom, root cause, and operator proof in `docs/issue_solve.md`
