## Context

P4 shipped a pure `travel_engine`, `OsrmRoutingProvider`, and a stub `ToolResult` / empty `execute_tool`. `docs/steps/step5.md` locks a phase-gated 12-tool agent; the first implementation cluster is **5.1 → 5.3** (schemas/registry + all tool bodies). Graph nodes, LangGraph, and `apply_tool_result` come later — tools must still be read-only → `ToolResult` so 5.5 can become the sole state writer.

Build contract: `docs/steps/step5.md` steps 5.1–5.3. SoT: `docs/blueprint_final.md` v6.1. Guardrails: `AGENT.md`.

## Goals / Non-Goals

**Goals:**

- Typed registry of exactly twelve tools with `AgentPhase` / `PHASE_TOOLS`
- `execute_tool` soft-fails unknown / wrong-phase / precondition / exceptions
- `get_tools_for_phase` returns OpenAI function schemas for the active phase only
- Real DISCOVER + PLAN/VALIDATE/control/REPLAN tool bodies calling travel_engine / search / readiness
- Named constants (`RANK_EXPLANATION_TOP_N`, `SEARCH_EXPAND_FACTOR`) — no magic numbers

**Non-Goals:**

- LangGraph, `TravelState`, agent/tool_executor nodes, narrative, evaluation persistence
- `maybe_transition_phase` / `apply_tool_result` / tool_trace increment (step 5.5)
- `PlannerService` SSE bridge or HTTP generate (5.12 / P6)
- Installing `langgraph`

## Decisions

1. **Extend P4 files in place** — grow `schemas.py` / `registry.py`; do not replace the soft-fail unknown path.
   - Alternative: new package under `planner/tools/v2` — rejected (breaks P4 tests and AGENT.md single registry).

2. **Phase check in `execute_tool` before fn** — wrong-phase → `precondition_failed` without calling the body. Phase comes from the read-only `state` snapshot (or ctx-held view until TravelState exists); do not put phase on `ToolContext`.
   - Alternative: trust LLM phase discipline — rejected (Decision Log #4).

3. **Tools return data only; no TravelState mutation** — bodies put readiness/candidates/routes/flags in `ToolResult.data`. Callers in 5.5+ apply via `apply_tool_result`. Until then, unit validations assert registry wiring and soft-fail codes.
   - Alternative: tools mutate a mutable ctx.state — rejected (Decision Log #16).

4. **DB session per tool acquire** — tools that need DB open a short-lived session inside the fn (prefer over holding `ctx.db` for 45s).
   - Alternative: one session on ToolContext for whole generation — deferred; optional only if measured need.

5. **search_places fallback** — Qdrant first; on empty/unavailable → PostGIS radius + `used_geo_fallback` in data.
   - Matches Resilience Contracts / AGENT.md named fallback.

6. **REPLAN / finish_plan coarse-graining** — multi-step engine work under one `execute_tool` call is intentional (step5 rationale). Sub-timings may live in `ToolResult.data`, not extra `tool_trace` entries.

7. **5.1 stubs then 5.2/5.3 replace** — register all 12 at 5.1 with `not_implemented` stubs; replace fns as bodies land so phase-filter tests stay green early.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Tool bodies accidentally mutate a shared state object | No writable TravelState on ToolContext; return `ToolResult` only; code review against step5 Decision Log #16 |
| Phase gating needs state before TravelState exists | `execute_tool(..., state=None)` accepts a duck-typed snapshot with `agent_phase`; tests use a simple namespace/object |
| Qdrant/OSRM flakiness in early tests | Unit validations use mocks / FakeRoutingProvider; live smoke is 5.14 |
| Overlap with later `apply_tool_result` | Document data keys tools emit; 5.5 owns merge semantics |
| Expanding envelope breaks P4 tests | Keep `unknown_tool` soft-fail; extend models additively (`fallback_used` optional default False) |

## Migration Plan

1. Implement 5.1 → run step5.1 ✅ snippet  
2. Implement 5.2 → register DISCOVER fns → ✅ snippet  
3. Implement 5.3 → remaining nine → ✅ snippet including finish_plan precondition  
4. Run `python -m pytest tests/ -v` (P4 planner envelope tests must still pass)  
5. Update `docs/context.md` Progress for 5.1–5.3; Next step → 5.4  

Rollback: revert the tools package commit; P4 stub behavior is restored.

## Open Questions

None blocking — contracts locked in `docs/steps/step5.md`. If `PHASE_TOOLS` placement (schemas vs registry) differs slightly from the validation import path, export from one module and re-export so the step5 snippet imports succeed.
