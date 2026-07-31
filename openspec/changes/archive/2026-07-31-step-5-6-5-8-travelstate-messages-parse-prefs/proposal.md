## Why

P5.1–5.5 delivered the 12-tool registry, `chat_with_tools` tests, and `apply_tool_result` / phase transitions, but the LangGraph surface is still stubs. Steps **5.6–5.8** (`docs/steps/step5.md`) add the serializable `TravelState`, phase-aware agent messages, and the fixed `parse_preferences` LLM bookend — the prerequisites for the agent↔executor loop (5.9+).

## What Changes

- Install and pin `langgraph==<exact verified version>` in `requirements.txt` (why-comment); run a 2-node hello-world proving `config["configurable"]["tool_context"]` passthrough
- Implement `src/planner/graph/state.py` — `TravelState` TypedDict (blueprint fields; no `db` / `routing` / `ToolContext`)
- Implement `src/planner/graph/messages.py` — `build_agent_messages(state)` with phase-aware system prompt + compact state summary
- Implement `src/planner/graph/nodes/parse_preferences.py` — fixed `chat_completion` JSON bookend with deterministic defaults on `WandrLLMError` / bad JSON
- Step ✅ validation snippets from `step5.md` 5.6–5.8 (mocked LLM for 5.8 — no live key required for this batch)

## Capabilities

### New Capabilities
- `planner-travel-state`: Serializable `TravelState` TypedDict + exact `langgraph` pin + configurable hello-world check (5.6)
- `planner-agent-messages`: Compact phase-aware `build_agent_messages` for `chat_with_tools` (5.7)
- `planner-parse-preferences`: Fixed pre-loop preference parse via `chat_completion` with fail-soft defaults (5.8)

### Modified Capabilities
- (none — existing `p5-phase-gated-tool-loop` / `p5-langgraph-runtime-hardening` already lock ToolContext-outside-state, list accumulation, and exact pin; this change implements those locks)

## Impact

- **Code:** `src/planner/graph/state.py`, `messages.py`, `nodes/parse_preferences.py` (replace stubs); `requirements.txt` gains `langgraph`
- **Non-goals:** agent / tool_executor nodes (5.9); narrative / evaluation bookends (5.10); graph builder (5.11); `PlannerService` SSE (5.12); pytest tool_loop / smoke (5.13–5.14); HTTP `/planner/generate` (P6)
- **LLM:** Implementation calls only `src/core/llm/client.py`. Batch validation uses mocks; a real `LLM_API_KEY` is **not** required to complete 5.6–5.8 proofs (needed later for 5.14 live smoke)
- **AGENT.md:** No I/O resources in `TravelState`; LLM only via core gateway; list fields last-write-wins (full list returned); `get_settings()` for `PLANNER_MAX_REPLAN_ATTEMPTS` default at invoke time
- **context.md:** After validations pass, mark 5.6–5.8 ✅ and set Next step to 5.9
