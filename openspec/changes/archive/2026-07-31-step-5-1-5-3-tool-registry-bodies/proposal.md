## Why

P4 left a minimal `ToolResult` / `execute_tool` stub; P5 cannot run a phase-gated agent until all twelve tools are registered and the DISCOVER + PLAN/VALIDATE/control/replan bodies exist. This is the first recommended OpenSpec batch from `docs/steps/step5.md` (steps **5.1–5.3**). There is no step 5.0 — P5 starts at 5.1.

## What Changes

- Expand `src/planner/tools/schemas.py`: `AgentPhase`, `PHASE_TOOLS`, `ToolResult` (+ `fallback_used`), `ToolTraceEntry`, `PendingToolCall`, `ToolContext`, and twelve Pydantic input models
- Expand `src/planner/tools/registry.py`: `TOOL_REGISTRY` with 12 `ToolDefinition`s, phase/precondition gating in `execute_tool`, `get_tools_for_phase`
- Implement DISCOVER tool bodies: `check_readiness`, `search_places`, `rank_places` (step 5.2)
- Implement remaining nine tool bodies: route/schedule/validate/finish/clarify + replan set (step 5.3)
- Stub fns only until their step lands; all soft-fail via `ToolResult` (never raise)
- No LangGraph, no graph nodes, no HTTP planner router (those are later P5 / P6 batches)

## Capabilities

### New Capabilities
- `planner-tool-registry`: Typed 12-tool registry surface — phases, ToolContext, execute gating, OpenAI schemas per phase (5.1)
- `planner-discover-tools`: Real DISCOVER tool bodies wired into the registry (5.2)
- `planner-plan-replan-tools`: PLAN / VALIDATE / control / REPLAN tool bodies + finish_plan precondition (5.3)

### Modified Capabilities
- `planner-tools-envelope`: Promote P4 stub contract to require full registry registration, `fallback_used`, and read-only tool → `ToolResult` behavior (unknown_tool soft-fail unchanged)

## Impact

- **Code:** `src/planner/tools/*` (schemas, registry, new per-tool modules, optional `constants.py`); may call `travel_engine/*`, `src/search/`, destinations readiness, places repository via tool boundary
- **Non-goals:** LangGraph / TravelState / agent nodes (5.6–5.11); `apply_tool_result` / phase transitions (5.5); `PlannerService` SSE (5.12); HTTP `/planner/generate` (P6); new packages (no `langgraph` until 5.6)
- **AGENT.md:** Tools return `ToolResult` only; no TravelState mutation; LLM only via core gateway (none in these tools); travel_engine stays pure; geo/search only through existing modules; `get_settings()` for caps/constants
- **Tests:** Step ✅ validation snippets from `step5.md` 5.1–5.3; full tool_loop pytest is 5.13 (later batch)
- **context.md:** Update Progress for 5.1–5.3 only after validations pass; do not mark P5 complete
