## 1. Independent step5 patches

- [x] 1.1 In `docs/steps/step5.md` step 5.2 / 5.3: add named constants `SEARCH_EXPAND_FACTOR = 1.5` and `RANK_EXPLANATION_TOP_N = 5`; add explicit `state.route`/`state.schedule` → `TripItinerary`/`DayPlan` mapping for `validate_itinerary`
- [x] 1.2 In step 5.3: paste REPLAN coarse-graining rationale (critic Fix 8) into the rationale section
- [x] 1.3 In step 5.6: replace `langgraph>=0.2.0` with exact-pin placeholder + hello-world 2-node compile/invoke + `configurable` passthrough check

## 2. ToolContext and sole-writer locks

- [x] 2.1 In step 5.1: remove “callbacks to mutate TravelState” from `ToolContext`; state that tools are read-only and `apply_tool_result` is the sole writer
- [x] 2.2 In step 5.5: document `unknown_tool` vs `tool_loop_count` + unconditional stuck-detector rationale (critic Fix 6); reinforce `apply_tool_result` as sole writer
- [x] 2.3 In locked `ToolContext vs TravelState` section: remove mutable-helper language; config-only injection preview

## 3. Agent / executor / graph / service rewrites

- [x] 3.1 Rewrite step 5.9 `agent_node`: never calls `execute_tool`; nudge then synthesize phase-default `pending_tool_calls`; ctx only from `config["configurable"]["tool_context"]`
- [x] 3.2 Rewrite step 5.9 `tool_executor_node`: sole `execute_tool` caller; read-append-return list fields; unconditional stuck-detector every cycle
- [x] 3.3 Rewrite step 5.11 edges: unconditional `agent → tool_executor`; remove dual-path edge notes
- [x] 3.4 Rewrite step 5.12 `PlannerService.generate`: fresh `ToolContext` per invoke via config; `last_known_state` outside cancellable task; timeout merges snapshot then `record_evaluation`

## 4. Tests and SoT alignment

- [x] 4.1 Extend step 5.13 with critic regression scenarios: concurrent ctx isolation, list accumulate across cycles, timeout nonempty evaluation, persistent unknown_tool hits stuck-detector, no-tool default goes through executor
- [x] 4.2 Update `docs/blueprint_final.md` ToolContext + agent no-tool fallback language to match config-only + synthesize-pending locks
- [x] 4.3 Add `AGENT.md` planner rule: ToolContext only via `config["configurable"]["tool_context"]` (no closures/globals)
- [x] 4.4 Mark `docs/steps/step5_critic.md` as applied companion (or add a one-line “applied into step5.md” header) so agents do not double-apply
- [x] 4.5 Grep `step5.md` for leftover “closure factory”, “callbacks to mutate”, `langgraph>=`, and agent-side `execute_tool` on default path — expect zero matches
