## Purpose

P5 phase-gated tool-loop agent: hardened Cursor prompt (`docs/steps/step5.md`), typed 12-tool registry, LangGraph agent↔executor loop, evaluation always, service SSE bridge (HTTP generate remains P6).

## Requirements

### Requirement: Hardened P5 Cursor prompt exists as step5.md
The project SHALL provide `docs/steps/step5.md` as the sole P5 implementation prompt, modeled on `docs/steps/step2.md` / `docs/steps/step4.md`.

The prompt MUST include:
- Prerequisites (P4 complete from `docs/context.md`)
- Prompt conventions and failure standards (`FAILURE BOUNDARY` + `✅ Failure path` per code step)
- P5 architecture / dependency graph and a single locked build order **5.1 → 5.14**
- Locked design decisions (no optional/either-or language for P5 contracts)
- Sub-steps **5.1–5.12** with clear TASK bodies, plus **5.13** pytest and **5.14** smoke/real verification
- Recommended OpenSpec **batched** implementation clusters (multiple sub-steps per apply)
- Full verification checklist and ship criteria table
- Citation that Planner SoT is `docs/blueprint_final.md` v6.1

#### Scenario: Agent can implement without inventing contracts
- **WHEN** an implementer opens `docs/steps/step5.md`
- **THEN** every P5 module has an ordered sub-step with explicit APIs, fallbacks, and a runnable ✅ validation command

#### Scenario: Blueprint remains SoT, prompt remains build contract
- **WHEN** product phase/tool/loop rules need authority
- **THEN** `docs/blueprint_final.md` v6.1 is cited as Planner SoT and `step5.md` encodes those locks for Cursor apply sessions

#### Scenario: Implementation uses batched OpenSpec applies
- **WHEN** implementers start coding from the prompt
- **THEN** the prompt documents cluster batches (e.g. 5.1–5.3, 5.4–5.5, 5.6–5.8, 5.9–5.11, 5.12–5.14) and MUST NOT require one propose→archive ceremony per micro-step

### Requirement: Typed tool registry with twelve tools and soft failures
The planner tool layer MUST expose exactly the twelve blueprint tools via `TOOL_REGISTRY` / `execute_tool(name, input, ctx)`: `check_readiness`, `search_places`, `rank_places`, `build_route`, `build_schedule`, `validate_itinerary`, `finish_plan`, `ask_clarification`, `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, `accept_partial`.

Every tool MUST have Pydantic input/output schemas. Tool failures and precondition failures MUST return `ToolResult(ok=False, code=...)` and MUST NEVER raise uncaught exceptions to the graph.

Nodes MUST call `execute_tool` only — never import tool implementation functions directly. `agent_node` MUST NOT call `execute_tool`; only `tool_executor_node` may.

#### Scenario: Wrong-phase tool is rejected without execution
- **WHEN** `execute_tool` is invoked for a tool not allowed in `state.agent_phase`
- **THEN** it returns `ToolResult(ok=False, code="precondition_failed")` (or equivalent phase code) without running the tool body

#### Scenario: Unknown tool soft-fails
- **WHEN** `execute_tool` is called with a name absent from the registry
- **THEN** it returns `ToolResult(ok=False, code="unknown_tool")` and does not raise

### Requirement: Phase-gated tool exposure and deterministic transitions
The system MUST define `AgentPhase` (`DISCOVER`, `PLAN`, `VALIDATE`, `REPLAN`, `WRAP_UP`) and `PHASE_TOOLS` mapping exactly as in blueprint_final v6.1.

`get_tools_for_phase(phase)` MUST return OpenAI-style function schemas for only that phase’s tools. Phase transitions MUST be applied by `maybe_transition_phase` from the blueprint transition table — the LLM MUST NOT choose the phase.

#### Scenario: Happy-path phase progression
- **WHEN** `rank_places`, then `build_schedule`, then `validate_itinerary` succeed in order
- **THEN** phase progresses DISCOVER → PLAN → VALIDATE → WRAP_UP

#### Scenario: Validation failure enters REPLAN when budget remains
- **WHEN** `validate_itinerary` returns errors and `replan_loop_count < max_replan_attempts`
- **THEN** phase transitions to REPLAN

### Requirement: ToolContext stays outside TravelState
`ToolContext` MUST carry `destination_id`, `base_lat`, `base_lng`, `routing: RoutingProvider`, and optional `db`. It MUST NOT expose mutation callbacks or a writable `TravelState` reference. `AsyncSession` and `RoutingProvider` MUST NOT be fields of LangGraph-checkpointed `TravelState`.

`ToolContext` MUST be threaded only via `config["configurable"]["tool_context"]` (no closures/module-globals). Tools that need DB access SHOULD acquire their own session (preferred) rather than holding one session for the full `PLANNER_GENERATION_TIMEOUT_SECONDS` window.

#### Scenario: TravelState has no db or routing fields
- **WHEN** `TravelState` is inspected
- **THEN** it has no `db` or `RoutingProvider` fields; those live on `ToolContext` / configurable injection

### Requirement: Bounded agent loop with no-tool nudge
The agent node MUST check `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` and force `WRAP_UP` with `abort_triggered=True` when exceeded.

When the LLM returns no tool calls, the agent MUST: append a system nudge, retry once with `tool_choice="required"`, and if still none, **synthesize** the phase-default as `pending_tool_calls` for `tool_executor_node` (DISCOVER → `check_readiness`) — never call `execute_tool` in the agent. Record the nudge/default path in warnings / `tool_trace` after executor runs.

Every `execute_tool` dispatch after a registry name resolves MUST increment `tool_loop_count` and append a `tool_trace` entry (`unknown_tool` does not increment).

#### Scenario: Max tool calls aborts to WRAP_UP
- **WHEN** `tool_loop_count` reaches `PLANNER_MAX_TOOL_CALLS`
- **THEN** `abort_triggered` is True and `agent_phase` becomes WRAP_UP

#### Scenario: No-tool path uses default after nudge
- **WHEN** the model returns content-only twice (auto then required)
- **THEN** `pending_tool_calls` contains the phase default, `tool_executor_node` executes it, and `tool_trace` records the nudge/default path

### Requirement: finish_plan requires validate-ok or abort
`finish_plan` MUST NOT succeed unless a prior `validate_itinerary` succeeded (`ok=True`) OR `state.abort_triggered=True`.

#### Scenario: finish_plan without validate fails soft
- **WHEN** `finish_plan` is called with no successful validate and `abort_triggered=False`
- **THEN** it returns `ToolResult(ok=False, code="precondition_failed")`

### Requirement: Narrative cannot mutate itinerary geometry
`write_narrative` MUST run outside the tool loop after plan completion. It MAY produce day titles and paragraphs only. It MUST NOT add, remove, reorder stops, or invent times/coordinates. On `WandrLLMError`, template narrative MUST be used and `llm_retry_count` incremented.

#### Scenario: Narrative failure still yields day text
- **WHEN** `chat_completion` raises `WandrLLMError` during narrative
- **THEN** template strings are applied per day and the graph continues to `record_evaluation`

### Requirement: Evaluation always recorded
`record_evaluation` MUST persist a generation record including `tool_trace`, `tool_loop_count`, `agent_phase_reached`, and resilience flags, including abort and partial-failure paths. Ranking explanations MUST live in `tool_trace` — not a new TripEvaluation column.

#### Scenario: Abort still writes evaluation
- **WHEN** generation ends with `abort_triggered=True`
- **THEN** an evaluation row is still written with non-empty `tool_trace` when tools ran

### Requirement: Graph bookends and compile gate
The compiled LangGraph MUST wire: `parse_preferences` → `agent` → `tool_executor` (unconditional), with conditionals for `needs_clarification` → END, `plan_complete` → `write_narrative` → `record_evaluation` → END, else loop to agent.

Graph compilation MUST succeed at import/startup (caught before first request). Package `langgraph` MUST be added to `requirements.txt` with an **exact** version pin and why-comment at the TravelState/graph step (5.6).

#### Scenario: Graph compiles with no orphan nodes
- **WHEN** the planner graph builder is imported/compiled
- **THEN** compilation succeeds and the locked node set is present with no orphans

### Requirement: Service SSE event bridge without P6 HTTP router
P5 SHALL implement a planner service-level SSE event bridge that maps tool/phase hooks to events (`tool_started`, `tool_done`, `phase_changed`) and wraps generation in `asyncio.wait_for(..., PLANNER_GENERATION_TIMEOUT_SECONDS)`.

P5 MUST NOT claim completion of `POST /api/v1/planner/generate` StreamingResponse, disconnect-cancel queue design, trips persistence, or `PLANNER_ABSOLUTE_MIN_PLACES` HTTP pre-graph floor — those remain P6 (forward-locked in the prompt Decision Log).

#### Scenario: Timeout surfaces as controlled failure
- **WHEN** generation exceeds `PLANNER_GENERATION_TIMEOUT_SECONDS`
- **THEN** the wait_for path fails controlled (error event / abort path) and MUST NOT hang indefinitely

### Requirement: P5 verification via pytest and smoke script
The prompt MUST specify `tests/planner/test_tool_loop.py` covering happy path, REPLAN ceiling, max-tool abort, and `ask_clarification` early exit; and `scripts/test_agent.py` for end-to-end Darjeeling proof with `tool_trace` printed.

Import guards MUST assert: no `litellm` outside `core/llm/client.py`; no direct tool impl imports in `planner/graph/nodes/`; travel_engine remains free of geo/httpx/LLM/DB.

#### Scenario: Happy-path tool loop stays bounded
- **WHEN** the happy-path integration test runs with mocked LLM/tools as specified
- **THEN** `plan_complete=True`, `tool_loop_count ≤ 8` (or prompt-locked ceiling for the fixture), and stops carry `suggested_start_time`

#### Scenario: Smoke fails loud by section
- **WHEN** a smoke section fails
- **THEN** the script exits non-zero with a clear section header and MUST NOT print an ambiguous overall PASS
