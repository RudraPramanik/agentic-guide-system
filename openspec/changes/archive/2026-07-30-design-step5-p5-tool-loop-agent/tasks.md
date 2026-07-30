## 1. Author hardened `docs/steps/step5.md`

- [x] 1.1 Write header + SoT pointers: blueprint_final v6.1, context.md, AGENT.md; state that blueprint is architecture SoT and step5 is the Cursor build contract; note OpenSpec = batched clusters
- [x] 1.2 Add Decision / Fix Log table locking P5 footguns (ToolContext vs TravelState, finish_plan precondition, no-tool nudge, narrative immutability, “core six” clarification, chat_with_tools already exists, SSE service vs P6 HTTP router, REPLAN prefer expand when dropped_stops)
- [x] 1.3 Add Prerequisites (P4 complete), Prompt conventions, FAILURE BOUNDARY / ✅ Failure path standards (match step2/step4)
- [x] 1.4 Add P5 architecture diagram + locked build order `5.1 → … → 5.14` (design D12)
- [x] 1.5 Lock design decisions in-doc: AgentPhase/PHASE_TOOLS, transition table, 12-tool registry, ToolContext DI, bounded ReAct, evaluate-always, design-pattern map (D1–D14)
- [x] 1.6 Author Steps **5.1–5.3** — schemas/registry + DISCOVER tools + PLAN/VALIDATE/control/replan tools — each with TASK, FAILURE BOUNDARY, ✅ validation
- [x] 1.7 Author Steps **5.4–5.5** — verify/harden `chat_with_tools` + phase gating/preconditions/transitions/tool_trace
- [x] 1.8 Author Steps **5.6–5.8** — TravelState (+ `langgraph` install), messages/prompt, `parse_preferences`
- [x] 1.9 Author Steps **5.9–5.11** — agent + tool_executor, write_narrative + record_evaluation, graph builder compile
- [x] 1.10 Author Steps **5.12–5.14** — service SSE bridge (not P6 HTTP router), pytest tool_loop, `scripts/test_agent.py` + context.md update rules
- [x] 1.11 Add P5 Complete verification checklist + ship criteria table + Recommended OpenSpec implementation batches (5.1–5.3, 5.4–5.5, 5.6–5.8, 5.9–5.11, 5.12–5.14)
- [x] 1.12 Ensure every code step has TASK body, FAILURE BOUNDARY, and runnable ✅ validation (Windows `Select-String` where grep would appear)

## 2. Align OpenSpec + process notes

- [x] 2.1 Confirm proposal/design/specs match the prompt locks (no embedding db/routing in TravelState; no narrative mutating stops; no claiming P6 HTTP generate)
- [x] 2.2 Emphasize in step5.md that implementation OpenSpec applies are **batched** for speed — not one propose→archive per micro-step
- [x] 2.3 Forward-lock only (do not implement in P5): absolute min-places HTTP floor, StreamingResponse disconnect-cancel queue, trips CRUD save, Redis planner cache

## 3. Apply gate (this change only)

- [x] 3.1 Verify `docs/steps/step5.md` exists and is non-empty with sections 5.1–5.14 + verification checklist
- [x] 3.2 Run `openspec status --change design-step5-p5-tool-loop-agent` and prepare archive after user review
- [x] 3.3 Do **not** mark P5 code complete in `docs/context.md` in this change — context updates land after implementation validations from the prompt
