## Why

`docs/steps/step5.md` (from `design-step5-p5-tool-loop-agent`) correctly locks P4→P5 forward contracts, but a LangGraph-runtime critic (`docs/steps/step5_critic.md`) found gaps that pass single-tool unit tests and then fail under concurrent, multi-turn graph use. Those gaps must be folded into `step5.md` (and aligned in `blueprint_final.md` where language still says “closure or configurable”) **before** implementing steps 5.9 / 5.11 / 5.12.

## What Changes

- Patch `docs/steps/step5.md` with the eight critic fixes + minor named-constant / itinerary-mapping notes (companion addendum already in `docs/steps/step5_critic.md`).
- Align ambiguous SoT wording in `docs/blueprint_final.md` and planner rules in `AGENT.md` where they still allow dual pathways (closure vs config; agent-side `execute_tool`; ToolContext mutation callbacks).
- **BREAKING (plan-level, pre-code):** remove “closure factory” and “callbacks to mutate TravelState” as allowed designs; remove agent-node direct `execute_tool` on the no-tool default path.
- Add regression scenarios to step 5.13 (concurrency leak, list accumulate, timeout evaluation, stuck-detector on unknown tools).
- No application code in this change — docs/planning locks only. Implementation remains `/opsx:apply` on the existing P5 clusters after the prompt is patched.

## Capabilities

### New Capabilities
- `p5-langgraph-runtime-hardening`: Locked LangGraph runtime contracts for P5 — ToolContext via `config["configurable"]` only; single `tool_executor` execution pathway; explicit list-state accumulation; timeout `last_known_state`; tools read-only + `apply_tool_result` sole writer; unconditional stuck-detector; exact `langgraph` pin; documented REPLAN coarse-graining.

### Modified Capabilities
- `planner-blueprint-sot`: Tighten P5 locks so ToolContext threading is config-only (not “closure / configurable”), and agent no-tool default is synthesize-pending → executor (not agent-side execute).
- `planner-tools-envelope`: Clarify that full P5 `execute_tool` receives a read-only state view and never mutates `TravelState`; unknown_tool soft-fail remains, with stuck-detector (not tool_loop_count) as the infinite-hallucination backstop.

## Impact

- **Docs:** `docs/steps/step5.md` (primary), `docs/blueprint_final.md` (SoT alignment), `AGENT.md` (planner-specific rule: config-only ToolContext), optionally keep `step5_critic.md` as applied-addendum reference.
- **Future code (not this change):** `planner/graph/nodes/agent.py`, `tool_executor.py`, `builder.py`, `service.py`, `tools/schemas.py` / `registry.py`, `requirements.txt` (`langgraph` exact pin), `tests/planner/`.
- **AGENT.md constraints that apply:** tool execution only via `execute_tool`; evaluation always recorded; `PLANNER_GENERATION_TIMEOUT_SECONDS` ceiling; phase gating; no magic numbers.
- **Non-goals:** implementing the P5 graph; changing travel_engine APIs; P6 SSE HTTP router; inventing new tools or phases; rewriting the whole blueprint.
- **Stub note (context.md):** planner LangGraph / tool bodies are still stubs — this change hardens the prompt so implementers do not ship the concurrent-leak / dual-path designs the critic flags.
