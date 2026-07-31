## Why

P5.1–5.3 registered and implemented all twelve tools, but the agent loop still cannot safely progress phases or merge tool outcomes into planning state. Step **5.4** locks the existing P0 `chat_with_tools` gateway with tests (no second LLM stack). Step **5.5** completes registry orchestration — preconditions, deterministic phase transitions, `apply_tool_result` as sole TravelState writer, and `tool_trace` / `tool_loop_count` bookkeeping. This is the second recommended OpenSpec batch from `docs/steps/step5.md` (`5.4–5.5`). Prerequisites 5.1–5.3 are ✅ in `docs/context.md`.

## What Changes

- Verify `src/core/llm/client.py` `chat_with_tools` matches the blueprint contract (tools + `tool_choice` → litellm; parse `tool_calls`; content-only; same tenacity / `WandrLLMError` path as `chat_completion`)
- Add `tests/core/test_llm_chat_with_tools.py` (mocked tool_call, content-only, exhausted-retries → `WandrLLMError`)
- Complete registry orchestration in `src/planner/tools/` (registry and/or small helpers): `check_preconditions`, `maybe_transition_phase`, `apply_tool_result`
- Harden `execute_tool` bookkeeping: after a registry name resolves, increment `tool_loop_count` once (including `precondition_failed`); `unknown_tool` does **not** increment; wrong-phase rejects before fn with no route/schedule side effects
- Expose / keep `get_tools_for_phase` as the only phase-filtered schema source for later agent nodes
- No LangGraph, TravelState TypedDict, graph nodes, or new packages

## Capabilities

### New Capabilities
- `llm-chat-with-tools`: Contract + unit tests for existing `chat_with_tools` / `LLMToolResponse` (step 5.4)
- `planner-phase-orchestration`: Phase preconditions, locked transition table, `apply_tool_result` sole writer, tool_trace / tool_loop_count rules (step 5.5)

### Modified Capabilities
- `planner-tool-registry`: `execute_tool` bookkeeping requirements — increment `tool_loop_count` on resolved names (not `unknown_tool`); orchestration helpers become part of the public planner-tools surface

## Impact

- **Code:** `src/core/llm/client.py` (verify only; harden if gaps); `tests/core/test_llm_chat_with_tools.py` (new); `src/planner/tools/registry.py` (+ optional helpers module); duck-typed mutable state snapshots until TravelState lands in 5.6
- **Non-goals:** LangGraph / `TravelState` TypedDict (5.6); messages / parse_preferences / agent↔executor nodes (5.7–5.9); stuck-detector implementation (5.9); narrative / evaluation / service SSE (5.10–5.12); HTTP generate (P6); installing `langgraph`
- **AGENT.md:** LLM only via core gateway; tools read-only → `ToolResult`; `apply_tool_result` sole writer; LLM never sets `agent_phase`; registry names only
- **Tests:** `pytest tests/core/test_llm_chat_with_tools.py -v`; step 5.5 import/transition validation; prefer `tests/planner/test_phase_transitions.py` for transition asserts (full tool_loop suite remains 5.13)
- **context.md:** After ✅ validation — mark 5.4–5.5 done; Next step → 5.6; update stubs (`apply_tool_result` / transitions no longer stub-only)
