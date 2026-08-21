## Context

See `proposal.md` for why. Constraints: AGENT.md (LLM only via `core/llm/client.py`; structure from travel_engine + tools; no invented endpoints/env). `agent_node` still must not call `execute_tool`. `DEFAULT_TOOL_BY_PHASE` stays as the last-resort map for VALIDATE / REPLAN / WRAP_UP. Live NVIDIA NIM `chat_with_tools` currently throws (`WandrLLMError`); generate MUST still produce a trip when search/rank/route/schedule can run without LLM tool selection.

## Goals / Non-Goals

**Goals:**

- Deterministic DISCOVER/PLAN fallback so a ready destination yields a usable schedule when the LLM does not pick tools.
- Stuck detector honest abort instead of fake-advancing into PLAN/VALIDATE with zero POIs.
- `build_route` fail-closed on empty place sets so empty 3-day routes are not `ok=True`.

**Non-Goals:**

- Fixing NVIDIA NIM / LiteLLM tool-calling format (log only if already cheap).
- Raising `PLANNER_GENERATION_TIMEOUT_SECONDS` or FE `AbortSignal` timeouts.
- Compose, CORS, cookies, or frontend copy for `generation_aborted`.
- New env vars or endpoints.

## Decisions

1. **State-aware default in `agent_node` (not a new graph node).**  
   Alternative: hardcoded LangGraph path that skips the agent. Rejected — would duplicate the tool loop and violate “agent decides, executor runs”. Shared helper `_default_tool_for_state(state)` used by both the no-tool and `WandrLLMError` paths. DISCOVER: readiness missing → `check_readiness`; else no candidates → `search_places`; else `rank_places`. PLAN: non-empty `route` → `build_schedule`; else `build_route`.

2. **Stuck DISCOVER/PLAN without work product aborts to WRAP_UP.**  
   Alternative: stay in phase forever (relies on max tool calls). Rejected for `unknown_tool` (does not increment `tool_loop_count`). Alternative: auto-advance anyway. Rejected — that is the live `generation_aborted` path. Warnings stay `phase_stuck*` so existing tests that look for that prefix still match.

3. **`build_route` returns `ok=False`, `code="no_ranked_places"` when both ranked and candidates are empty.**  
   Keep the existing auto-rank-from-candidates branch when search already ran. Do not write a successful empty `route` list of blank days.

4. **Proof is live SSE + pytest, not a timeout bump.**  
   Destination `458854b1-…` (132 places) after Compose `up`. Document in `docs/issue_solve.md`.

## Risks / Trade-offs

- [Risk] Search/Qdrant empty even after `search_places` → still `generation_aborted`. → Mitigation: geo fallback already in `search_places`; abort remains honest.
- [Risk] Extra search/rank LLM-less cycles add wall time. → Mitigation: tools are in-process/DB; live abort today is ~7s doing nothing useful.
- [Risk] Tests that assume DISCOVER default is always `check_readiness` after readiness is set. → Mitigation: first cycle still `check_readiness` on empty initial state; update only tests that stub readiness then expect another check.

## Migration Plan

Deploy with API source bind-mount / image rebuild. No DB migration. Rollback: revert the three Python files. No FE deploy required.

## Open Questions

None.
