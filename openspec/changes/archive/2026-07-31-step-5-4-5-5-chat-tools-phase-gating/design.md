## Context

P5.1–5.3 shipped a 12-tool `TOOL_REGISTRY` with phase checks and soft-fail `execute_tool`, but no `apply_tool_result`, no `maybe_transition_phase`, and no `tool_loop_count` / `tool_trace` bookkeeping. `chat_with_tools` already exists in `src/core/llm/client.py` from P0 and already passes `tools` / `tool_choice` — step 5.4 is verify + tests only. Build contract: `docs/steps/step5.md` **5.4–5.5**. SoT: `docs/blueprint_final.md` v6.1. Guardrails: `AGENT.md`. Critic locks for sole-writer and `unknown_tool` + stuck-detector rationale are already merged into `step5.md`.

## Goals / Non-Goals

**Goals:**

- Prove `chat_with_tools` contract with unit tests (mocked litellm)
- Implement `check_preconditions`, `maybe_transition_phase`, `apply_tool_result` on the registry surface
- Deterministic phase transitions per locked table; LLM never sets `agent_phase`
- Sole TravelState-from-tools writer: `apply_tool_result` merges `ToolResult.data`, appends full `tool_trace`, applies `tool_loop_count` rules
- Wrong-phase / precondition fail → `precondition_failed`, fn not called, no route/schedule mutation

**Non-Goals:**

- LangGraph, `TravelState` TypedDict, agent/tool_executor nodes, stuck-detector runtime (5.6 / 5.9)
- Narrative, evaluation persistence, PlannerService SSE, HTTP generate
- Rewriting litellm gateway or adding a second LLM client
- New packages (`langgraph` waits for 5.6)

## Decisions

1. **5.4 = verify, do not rewrite** — If `chat_with_tools` already matches the contract, only add tests. Harden only if a gap is found (e.g. missing `tool_choice` pass-through — already present).
   - Alternative: reimplement gateway — rejected (Decision Log #3; AGENT.md single gateway).

2. **Orchestration helpers live next to the registry** — Prefer `registry.py` exports (`check_preconditions`, `maybe_transition_phase`, `apply_tool_result`) with a small helper module only if file size warrants it. Duck-typed mutable mapping/namespace until `TravelState` (5.6).
   - Alternative: wait for TypedDict TravelState — rejected; 5.5 must land before 5.6 so nodes can import helpers.

3. **Split write responsibilities (reconcile 5.5 vs 5.9 wording)** —
   - `execute_tool`: soft-fail dispatch only; may accept optional mutable `state` for phase/precondition reads; MUST NOT merge `result.data` into route/schedule itself.
   - `apply_tool_result(state, name, result, *, duration_ms=...)`: **sole writer** — merge known `data` keys per tool, append `ToolTraceEntry` (read-append full list), increment `tool_loop_count` when `name in TOOL_REGISTRY` (including precondition_failed outcomes that never ran fn). Do **not** increment when `result.code == "unknown_tool"`.
   - `maybe_transition_phase(state, tool_name, result)`: apply locked table after apply; increment `replan_loop_count` only on entry into REPLAN.
   - Call sequence for future `tool_executor_node` (5.9): time → `execute_tool` → `apply_tool_result` → `maybe_transition_phase`. Step 5.5’s “execute_tool MUST increment” is satisfied by the orchestration path owned by these registry helpers (documented so 5.9 does not invent a second writer).
   - Alternative: mutate counters inside `execute_tool` — rejected as dual-writer risk with `apply_tool_result` (Decision Log #16 / critic Fix 5).

4. **Locked transition table (verbatim from step5)** —

   | From | Condition | To |
   |------|-----------|-----|
   | DISCOVER | `rank_places` succeeded | PLAN |
   | PLAN | `build_schedule` succeeded | VALIDATE |
   | VALIDATE | `validate_itinerary` ok=True | WRAP_UP |
   | VALIDATE | errors AND `replan_loop_count < max` | REPLAN (+increment on entry) |
   | VALIDATE | errors AND replan exhausted | WRAP_UP (`abort_triggered=True`) |
   | REPLAN | any replan tool ok except `accept_partial` | PLAN |
   | REPLAN | `accept_partial` OR replan max | WRAP_UP |
   | Any | `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` | WRAP_UP (`abort_triggered=True`) |
   | DISCOVER | `ask_clarification` succeeded | `needs_clarification=True` (END path later) |

   Max replan / max tool calls from `get_settings()` (`PLANNER_MAX_REPLAN_ATTEMPTS`, `PLANNER_MAX_TOOL_CALLS`).

5. **`apply_tool_result` field merge map** — Merge only keys present in `result.data` that the tool is allowed to set (e.g. `candidate_pois`, `ranked_pois`, `route`, `schedule`, `validation_result`, `last_validate_ok`, `readiness_score`, `used_geo_fallback`, `used_osrm_fallback`, `abort_triggered`, `plan_complete`, `needs_clarification`, `clarification_question`, `warnings`/`errors` as full-list appends). Never invent place IDs. Never raise — bad/missing data → skip or append warning.
   - Alternative: tools mutate state via callbacks — forbidden.

6. **`unknown_tool` + stuck-detector (document, do not implement detector)** — Do not increment `tool_loop_count` for unknown names. Rationale (locked): safe only because 5.9 stuck-detector runs every cycle. Do not implement stuck-detector here; leave a comment pointing at 5.9.

7. **Test state helper** — Provide `_make_test_state()` (or test fixtures) with `agent_phase`, `tool_loop_count`, `tool_trace`, `replan_loop_count`, `max_replan_attempts` for transition tests — matches step 5.5 validation snippet.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Dual bookkeeping between `execute_tool` and `apply_tool_result` | Decision 3: only `apply_tool_result` writes counters/trace/data |
| Phase transitions before TravelState TypedDict | Duck-typed dict/namespace; 5.6 ports fields without changing helper signatures |
| `tool_loop_count` ceiling check lives in agent (5.9) vs `maybe_transition_phase` | Implement Any→WRAP_UP abort in `maybe_transition_phase` when count already ≥ max after increment; agent also gates before calling tools |
| Partial merge map wrong for a tool | Prefer explicit per-tool allowlist; extend in 5.13 when fixtures fail |
| LLM tests flake on real network | Mock `litellm.acompletion` only; never hit live provider in unit tests |

## Migration Plan

1. Land 5.4 tests first (no behavior change expected).
2. Add orchestration helpers + wire call sites for tests.
3. Run step ✅ validations; update `docs/context.md` (Next → 5.6).
4. Rollback = revert change; no DB/migrations.

## Open Questions

None blocking — transition table and sole-writer rule are locked in `step5.md`. If `apply_tool_result` vs `execute_tool` wording conflicts during apply, prefer Decision 3 and ask only if tests cannot express the locked failure path.
