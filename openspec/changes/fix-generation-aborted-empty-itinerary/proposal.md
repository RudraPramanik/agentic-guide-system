## Why

Guest `POST /planner/generate` on a ready destination (Darjeeling, 132 places) streams SSE then ends with terminal `error` / `generation_aborted`. The UI title “Generation failed” is contract-correct. Live proof (2026-08-21): the graph never called `search_places` / `rank_places`; NVIDIA NIM `chat_with_tools` failed (`llm_retry_count=12`) so the agent synthesized `DEFAULT_TOOL_BY_PHASE` (`check_readiness` forever); the stuck detector then auto-advanced DISCOVER→PLAN with zero POIs; `build_route` returned `ok=True` for empty ranked sets; `finish_plan` completed with an empty schedule. Generate is unusable until the fallback path still builds a real itinerary (structure from code).

## What Changes

- Make the agent’s synthesized default tool **state-aware**: DISCOVER progresses `check_readiness` → `search_places` → `rank_places`; PLAN prefers `build_schedule` once a route exists.
- Stop the stuck detector from auto-advancing DISCOVER with zero `candidate_pois`, or PLAN with no usable schedule.
- `build_route` MUST NOT return `ok=True` when there are no ranked/candidate places to allocate.
- Document the failure and operator proof in `docs/issue_solve.md`.
- No new endpoints, env vars, or FE abort-timeout changes. Not **BREAKING** for successful generates.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `planner-agent-tool-executor`: synthesized no-tool / `WandrLLMError` defaults MUST pick the next productive phase tool from TravelState, not a static `DEFAULT_TOOL_BY_PHASE` map; stuck auto-advance MUST NOT skip search or skip an empty PLAN into VALIDATE.
- `planner-plan-replan-tools`: `build_route` on an empty ranked+candidate set is a soft-fail (`ok=False`), not a successful empty route.
- `planner-sse-generate`: a cold generate on a destination that already passed the min-places floor MUST attempt place search before wrapping up as `generation_aborted` solely because the LLM did not pick tools.

## Impact

- Code: `src/planner/graph/nodes/agent.py`, `src/planner/tools/orchestration.py` (`run_stuck_detector`), `src/planner/tools/build_route.py`, tests under `tests/planner/`.
- Docs: `docs/issue_solve.md`. Compose / Settings / FE unchanged.
- AGENT.md: LLM still only via `core/llm/client.py`; places still from search/rank tools + travel_engine, never invented by the LLM.
- Live proof: Docker `up`, `POST /api/v1/planner/generate` on destination `458854b1-4d2a-4d02-8901-e26ed59c0c8b` yields `itinerary_done` + `trip_id`.
