## Context

P5.1–5.8 are done: 12-tool registry, `apply_tool_result` / `maybe_transition_phase`, `TravelState`, `build_agent_messages`, and `parse_preferences`. Graph modules `agent.py`, `tool_executor.py`, `write_narrative.py`, `record_evaluation.py`, and `builder.py` remain step-0.1 stubs (~1 line). Evaluation `repository.py` / `service.py` are stubs; `TripEvaluation` model columns already cover tool_trace / resilience / abort.

This batch implements **5.9–5.11** from `docs/steps/step5.md` (OpenSpec cluster 4). SoT: `docs/blueprint_final.md` v6.1. Guardrails: `AGENT.md`. Runtime locks already in `openspec/specs/p5-langgraph-runtime-hardening` and `p5-phase-gated-tool-loop`.

## Goals / Non-Goals

**Goals:**

- Ship bounded `agent_node` (decide only) + `tool_executor_node` (sole `execute_tool`) with phase-default synthesize, max-call abort, and unconditional stuck-detector
- Ship fixed bookends: narrative (titles/paragraphs only) + always-on evaluation persistence
- Compile and cache the planner LangGraph with locked edges (agent → tool_executor unconditional)
- Pass step5 ✅ import / compile / import-guard snippets for 5.9–5.11

**Non-Goals:**

- `PlannerService.generate` SSE callbacks / `asyncio.wait_for` (5.12)
- Full tool-loop pytest suite (5.13) and live smoke (5.14)
- HTTP planner router / StreamingResponse (P6)
- New TripEvaluation columns or Alembic migrations
- New third-party packages (langgraph already pinned in 5.6)

## Decisions

1. **Agent never executes tools** — `agent_node` only returns `pending_tool_calls` (LLM calls, post-nudge calls, or synthesized `PendingToolCall` for `DEFAULT_TOOL_BY_PHASE[phase]` with `arguments_json="{}"`). On `WandrLLMError`, same synthesize path + `llm_retry_count += 1`.
   - Alternative: agent calls `execute_tool` on default — **forbidden** by AGENT.md / Decision Log / hardening spec.

2. **`DEFAULT_TOOL_BY_PHASE` lives next to phase constants** — add dict on `schemas.py` (or tiny helper module under `planner/tools/`) matching the locked table (DISCOVER→`check_readiness`, PLAN→`build_route`, VALIDATE→`validate_itinerary`, REPLAN→`reoptimize_routes`, WRAP_UP→`finish_plan`). Do not hardcode string literals inside the node body beyond looking up the map.

3. **`parse_tool_input(name, arguments_json)` soft-fails** — JSON-parse + validate against `TOOL_REGISTRY[name].input_model`. Unknown name / bad JSON / validation error → return a sentinel empty model or let `execute_tool` return `unknown_tool` / soft fail — never raise out of `tool_executor_node`. Prefer implementing as a registry helper exported for the executor.

4. **Stuck-detector is unconditional every executor cycle** — fingerprint = phase + lengths of candidates/ranked/route/schedule (+ compact last validation error codes if cheap). Track consecutive unchanged cycles on state (e.g. `_stuck_fingerprint` / `_stuck_cycles` as internal TravelState keys, or fields already present — prefer minimal new optional TypedDict keys documented as loop-internal). When `>= PLANNER_AGENT_PHASE_STUCK_LIMIT`:
   - DISCOVER/PLAN/VALIDATE → auto-advance happy-path next phase + warning `phase_stuck_auto_advance`
   - REPLAN → `abort_triggered=True`, WRAP_UP, warning `phase_stuck_replan_abort`
   - WRAP_UP → force finish/plan_complete attempt path per step5 (set state so conditional can exit; do not invent tools outside WRAP_UP allowlist)
   - Never gate the detector on “real tool succeeded” (unknown_tool hole).

5. **List accumulation in executor** — `working_state = dict(state)`; for each pending call: `execute_tool` → `apply_tool_result` → `maybe_transition_phase`; clear `pending_tool_calls`; run stuck detector; return the full working dict (full `tool_trace` / `warnings` / `errors` lists).

6. **Narrative is structure-preserving** — input = locked schedule/route; `chat_completion` asks for day titles + paragraphs only; post-filter any LLM-mentioned place_ids not in schedule (strip/ignore); merge into `state.itinerary` without touching stop order/times/coords. `WandrLLMError` → per-day templates + `llm_retry_count += 1`.

7. **Evaluation service owns persistence** — `EvaluationService.record_generation(...)` maps TravelState fields onto existing `TripEvaluation` columns; `EvaluationRepository` flush/commit pattern matches other domain repos (short-lived session inside node/service). DB failure → log + append warning; do not raise through the graph. Always invoked for abort / clarification / success when the graph reaches that node; clarification END may skip narrative but **5.11 wiring** ends clarification at END without narrative — evaluation for clarification paths that skip `record_evaluation` node is deferred to 5.12 service bridge if needed. **This batch follows step5.11 edges literally:** `needs_clarification → END` (no evaluation node on that edge). Prefer documenting that 5.12 service MUST still call `record_evaluation` for clarification/timeout when the graph short-circuits — do not silently rewire 5.11 against the prompt.
   - Clarification: step5.11 says `needs_clarification → END`. Step5.10 says evaluation ALWAYS runs including clarification. **Resolve:** keep graph edges as step 5.11; in design, note that clarification persistence is a **5.12 service responsibility** (call `record_generation` after graph returns with `needs_clarification=True`). Abort-with-`plan_complete` still hits narrative→evaluation. Max-tools WRAP_UP should still progress toward `finish_plan` / `plan_complete` so evaluation runs via the happy bookend path when possible.

8. **Compiled graph singleton** — `build_planner_graph()` / `get_compiled_graph()` compile once, cache module-level. Compile errors must raise at import/startup. No ToolContext closure on nodes.

9. **Validation for this batch** — 5.9 import + Select-String guards (no tool-impl imports; no `execute_tool(` in agent.py); 5.10 imports; 5.11 compile. Defer behavioral loop tests to 5.13.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Clarification path skips `record_evaluation` node vs “ALWAYS runs” lock | Graph follows 5.11; 5.12 service must persist on clarification/timeout short-circuit — call out in tasks + context note |
| Stuck fingerprint too coarse → false auto-advance | Include phase + list lengths + last validation codes; limit from `get_settings()` |
| Agent nudge mutates messages incorrectly | Nudge is ephemeral for the retry call only unless step requires appending to state warnings (`agent_nudged` / `agent_no_tool_call_default_used`) |
| Evaluation repo pattern diverges from BaseRepository | Follow existing repository conventions; flush-only + commit at service boundary |
| Implementer imports tool bodies into nodes | ✅ Select-String guard in tasks; review against AGENT.md |

## Migration Plan

1. Add helpers (`DEFAULT_TOOL_BY_PHASE`, `parse_tool_input`, `run_stuck_detector`)
2. Implement `agent_node` → `tool_executor_node`
3. Implement narrative + evaluation repo/service + `record_evaluation` node
4. Implement `builder.py` compile + cache
5. Run step5 ✅ snippets for 5.9–5.11
6. Update `docs/context.md` (5.9–5.11 ✅, Next = 5.12)
7. Rollback: revert the listed modules to stubs (no schema migration to undo)

## Open Questions

- None blocking for propose. Clarification-vs-evaluation edge conflict is resolved by deferring clarification persistence to 5.12 service (documented above) — if product insists evaluation must be a graph node on clarification too, that would be a step5.md amendment before apply.
