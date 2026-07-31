## Context

P5.1–5.5 are done: 12-tool registry, `chat_with_tools` tests, and `apply_tool_result` / `maybe_transition_phase`. Graph modules under `src/planner/graph/` remain step-0.1 stubs (~1 line). This batch implements **5.6–5.8** from `docs/steps/step5.md`: serializable `TravelState`, phase-aware agent messages, and the fixed `parse_preferences` bookend — so 5.9 can wire agent↔tool_executor without inventing state shape.

SoT: `docs/blueprint_final.md` v6.1. Guardrails: `AGENT.md`. Existing locks already in `openspec/specs/p5-langgraph-runtime-hardening` and `p5-phase-gated-tool-loop`.

## Goals / Non-Goals

**Goals:**

- Pin exact `langgraph` and prove `config["configurable"]["tool_context"]` round-trips via a trivial 2-node graph
- Define `TravelState` TypedDict with blueprint fields; forbid I/O resources on state
- Build compact `build_agent_messages` (phase + allowed tools + REPLAN guidance + last 5 traces)
- Implement `parse_preferences` via `chat_completion` with fail-soft defaults (never blocks the graph)

**Non-Goals:**

- `agent_node` / `tool_executor_node` (5.9)
- `write_narrative` / `record_evaluation` (5.10)
- `graph/builder.py` compile of the full planner graph (5.11)
- `PlannerService` SSE / timeout (5.12)
- Full tool_loop pytest / live smoke (5.13–5.14)
- HTTP planner router (P6)
- Live LLM calls for ✅ validation of this batch (mocks only)

## Decisions

1. **TypedDict `TravelState` (not a Pydantic model / dataclass)** — matches LangGraph StateGraph conventions and blueprint; `total=False` where invoke may omit optional working fields.
   - Alternative: Pydantic BaseModel — rejected for this step (checkpoint/serialization patterns in step5 assume TypedDict; can revisit later if validation-at-boundary is needed).

2. **No `Annotated` reducers for list fields in P5** — `tool_trace`, `warnings`, `errors` are last-write-wins; nodes must return the full extended list. Document in state module docstring; do not add reducers “for convenience.”
   - Alternative: operator.add reducers — rejected (Decision Log #14 / runtime hardening spec).

3. **Exact `langgraph` pin after hello-world** — install candidate, run 2-node + conditional edge + configurable sentinel check, then write `langgraph==X.Y.Z` (never `>=`). Prefer a recent 0.2.x that imports cleanly on the project’s Python.
   - Alternative: leave floating pin — forbidden by step5 / hardening spec.

4. **Hello-world lives as a throwaway script or inline ✅ snippet** — not part of the production graph builder (builder stays stub until 5.11). Purpose is API discovery only.
   - Alternative: start `builder.py` now — rejected (scope creep; full shape locked in 5.11).

5. **`build_agent_messages` is pure / sync** — reads state dict only; no LLM, no DB. Allowed tool names come from `PHASE_TOOLS[phase]` (import from tools schemas). Missing optional fields → safe defaults (empty lists, unknown phase → DISCOVER or empty tool list without raising).
   - REPLAN + `dropped_stops` present → system text MUST prefer `expand_poi_search` over `drop_weakest_stop` (step5 Decision Log #7).

6. **`parse_preferences` uses `chat_completion` only** — not `chat_with_tools`; JSON `response_format`. On `WandrLLMError` or unparseable content → defaults (`days=3`, `budget="mid"`, `interests=[]`, offbeat/trekking false) and `llm_retry_count += 1`. Map obvious interest strings toward `PLACE_TAG_VOCAB`; keep unknowns.
   - Resilience: LLM failure is a named soft path (defaults), matching Resilience Contracts for parse bookend — never abort generation solely because parse failed.

7. **Validation strategy for this batch** — 5.6/5.7 import + assert snippets; 5.8 AsyncMock `WandrLLMError` + mocked happy-path JSON. No requirement to hit a real provider during apply.
   - Live key remains useful for later 5.14 smoke and optional manual parse checks; not a gate for 5.6–5.8.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Wrong langgraph minor breaks `configurable` / StateGraph API mid-5.11 | Hello-world in 5.6 before designing full graph; pin exact version |
| Agents put `db`/`routing` on TravelState “temporarily” | Type hints assert + step ✅; review against FORBIDDEN list |
| List-field silent drop when nodes return deltas | Docstring + hardening lock; 5.9/5.13 tests will enforce full-list returns |
| `parse_preferences` interest mapping too aggressive | Prefer vocab intersection / obvious aliases only; unknown interests kept (scoring may yield 0) |
| Implementer assumes live LLM needed and blocks | Proposal + tasks state mocks suffice; `.env` key optional until smoke |

## Migration Plan

1. `pip install` pinned langgraph; append `requirements.txt` with why-comment
2. Replace stubs: `state.py` → `messages.py` → `parse_preferences.py`
3. Run step5 ✅ snippets for 5.6–5.8
4. Update `docs/context.md` (5.6–5.8 ✅, Next = 5.9)
5. Rollback: revert the three modules to stubs + remove langgraph pin if install proves incompatible (unlikely after hello-world)

## Open Questions

- None blocking. Exact `langgraph` version is determined at apply time via hello-world (not pre-pinned in this design).
