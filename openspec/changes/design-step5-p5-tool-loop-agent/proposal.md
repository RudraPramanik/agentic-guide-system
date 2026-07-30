## Why

P4 is complete (pure `travel_engine`, CORS, `OsrmRoutingProvider`, thin `ToolResult`/`execute_tool` stub). `docs/steps/step5.md` is empty while `docs/blueprint_final.md` v6.1 locks the P5 phase-gated tool-loop agent at the product level. Agents still need a step2/step4-style Cursor build prompt — sub-steps, failure boundaries, ✅ validation, pytest, smoke — before coding. Without that contract, implementers re-open either/or on `ToolContext` vs `TravelState`, unbounded ReAct, narrative mutating geometry, or full HTTP SSE that belongs in P6.

## What Changes

- Author **`docs/steps/step5.md`** as the hardened P5 Cursor prompt (same shape as `step2.md` / `step4.md`): prerequisites, architecture diagram, locked decisions, ordered sub-steps **5.1–5.14**, each with TASK / FAILURE BOUNDARY / ✅ validation where code lands.
- Align this change’s design/specs/tasks to **`docs/blueprint_final.md` v6.1** Planner SoT (principles 6–13 + AGENT.md + Resilience Contracts + P5 phase blueprint).
- Lock abstractions in the prompt: 12 typed tools, `AgentPhase` / `PHASE_TOOLS`, deterministic phase transitions, `ToolContext` outside LangGraph state, bounded tool loop, no-tool nudge, narrative outside loop, evaluation always recorded, service-level SSE event bridge (HTTP router stays P6).
- Encode **batched OpenSpec implementation clusters** (multiple sub-steps per apply) for development speed — same cadence as P4, not one ceremony per micro-step.
- **Non-goals for this design change’s apply:** no production planner graph/tool body code until a follow-on apply from the prompt. Primary deliverable is the prompt + OpenSpec alignment.

## Capabilities

### New Capabilities

- `p5-phase-gated-tool-loop`: Contract for the P5 planner agent — typed tool registry + 12 tool bodies, phase gating/preconditions/transitions, TravelState + messages, fixed bookend nodes (`parse_preferences`, `write_narrative`, `record_evaluation`), agent↔tool_executor loop, LangGraph compile, planner service SSE event bridge, pytest + `scripts/test_agent.py` — as specified in the hardened `docs/steps/step5.md` prompt.

### Modified Capabilities

<!-- Intentionally empty: no archived main-spec requirement deltas; this change authors the build prompt + delta specs under the change. -->

## Impact

- **Docs:** `docs/steps/step5.md` becomes the sole P5 implementation prompt. Blueprint remains architecture SoT, not the Cursor prompt.
- **Code (once implemented from the prompt):** `src/planner/tools/*` (today stubs + P4 envelope), `src/planner/graph/*`, `src/planner/service.py` SSE bridge, `src/evaluation/*` record path, `langgraph` package at the graph step; `chat_with_tools` already exists from P0 — prompt verifies/hardens + tests, does not reinvent.
- **AGENT.md:** tools only via `execute_tool`; LLM only via `core/llm/client.py`; nodes never call tool impls or invent tools; travel_engine stays pure; evaluation never skipped.
- **Tests:** FakeRoutingProvider + mocked LLM/Qdrant; phase-transition unit tests; tool-loop integration; smoke via `scripts/test_agent.py`.
- **Process:** propose → apply (write step5.md) → archive this design change; then implement P5 from the prompt in **batched** OpenSpec applies (e.g. 5.1–5.3, 5.4–5.5, 5.6–5.8, 5.9–5.11, 5.12–5.14).
- **Non-goals:** `POST /planner/generate` HTTP router + trips CRUD persistence (P6); edit/replan API (P7); Redis cache; `PLANNER_ABSOLUTE_MIN_PLACES` pre-graph HTTP floor (P6 — design-only forward lock in step5).
