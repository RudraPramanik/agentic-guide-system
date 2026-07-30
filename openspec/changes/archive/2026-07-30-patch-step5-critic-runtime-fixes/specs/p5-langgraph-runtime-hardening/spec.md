## ADDED Requirements

### Requirement: ToolContext threaded only via RunnableConfig
The P5 planner prompt and eventual implementation MUST obtain `ToolContext` exclusively from `config["configurable"]["tool_context"]` on every node invocation. Closures bound at graph-compile time, module-level context globals, and any other shared mutable ctx holder are FORBIDDEN.

`docs/steps/step5.md` MUST state this lock in steps 5.9 and 5.12 and MUST require an `AGENT.md` planner rule to the same effect. Step 5.13 MUST include a concurrent-generation regression that two `generate()` calls with different `destination_id`s against one cached compiled graph each see their own context.

#### Scenario: Concurrent generations do not share ToolContext
- **WHEN** two concurrent `PlannerService.generate` calls use different destination IDs against the same cached compiled graph
- **THEN** each tool/node execution observes only its own `ToolContext.destination_id` (no cross-request leak)

### Requirement: Single tool-execution pathway through tool_executor
`agent_node` MUST NEVER call `execute_tool`. It MUST only set `pending_tool_calls` (from the LLM, after nudge, or as a synthesized phase-default call). `tool_executor_node` MUST be the sole caller of `execute_tool`. The compiled graph MUST edge `agent → tool_executor` unconditionally each cycle.

`docs/steps/step5.md` steps 5.9 and 5.11 MUST be rewritten to this shape (removing agent-side default `execute_tool`).

#### Scenario: No-tool path synthesizes default for executor
- **WHEN** the LLM returns no tool calls even after one `tool_choice="required"` nudge
- **THEN** `pending_tool_calls` contains the phase default tool, `tool_executor_node` performs the only `execute_tool` call, and `tool_trace` records the default path with a nudge/default warning

### Requirement: Explicit Python accumulation for list-shaped TravelState fields
Nodes that touch list-shaped `TravelState` fields (`tool_trace`, `warnings`, `errors`) MUST read the current full list, append in Python, and return the complete extended list. Implementations MUST NOT rely on LangGraph `Annotated` reducers or return only the newest entry.

#### Scenario: tool_trace survives multiple cycles
- **WHEN** four scripted `tool_executor_node` cycles each append one trace entry
- **THEN** `len(final_state["tool_trace"]) == 4` (not 1)

### Requirement: Timeout path captures last_known_state outside the cancelled task
`PlannerService.generate` MUST maintain a service-level `last_known_state` (or equivalent) updated by the same emit/checkpoint hooks used for SSE events, living outside the `asyncio.wait_for`-cancellable graph task. On `TimeoutError`, the service MUST build a final state from that snapshot (plus timeout error / `abort_triggered`), then still run `record_evaluation`.

#### Scenario: Timeout evaluation retains pre-timeout progress
- **WHEN** generation times out after at least one tool_executor cycle has emitted a state snapshot
- **THEN** the evaluation record includes a non-empty `tool_trace` (not only `errors=["generation_timeout"]`)

### Requirement: Tools are read-only; apply_tool_result is the sole TravelState writer
`ToolContext` MUST NOT expose callbacks or a writable `TravelState` reference for tools to mutate. Tools MUST return `ToolResult` only. `apply_tool_result` inside `tool_executor_node` MUST be the sole writer of planning state from tool outcomes. Step 5.1 language about “callbacks to mutate allowed TravelState fields” MUST be removed from `docs/steps/step5.md`.

#### Scenario: Tool body cannot write TravelState
- **WHEN** a tool implementation runs
- **THEN** it has no API to mutate `TravelState` directly; state changes appear only after `apply_tool_result` merges `ToolResult.data`

### Requirement: Stuck-detector runs every tool_executor cycle
The phase stuck-detector MUST run unconditionally at the end of every `tool_executor_node` cycle, including cycles that only resolved `unknown_tool` or precondition failures. `docs/steps/step5.md` MUST document that `unknown_tool` not incrementing `tool_loop_count` is safe only because of this unconditional detector.

#### Scenario: Persistent unknown tools abort via stuck-detector
- **WHEN** the LLM repeatedly names a nonexistent tool every cycle
- **THEN** the run terminates via stuck-detector / `abort_triggered` within `PLANNER_AGENT_PHASE_STUCK_LIMIT` cycles — not by exhausting `tool_loop_count` and not by waiting for the wall-clock generation timeout alone

### Requirement: Exact langgraph pin and hello-world compile check
Step 5.6 MUST add `langgraph==<exact tested version>` to `requirements.txt` (no floating `>=`). Before committing the full graph shape in 5.11, step 5.6 MUST include a trivial two-node compile-and-invoke check confirming `StateGraph`, conditional edges, and `config["configurable"]` passthrough for the pinned version.

#### Scenario: Floating pin forbidden in step5
- **WHEN** step 5.6 dependency text in `docs/steps/step5.md` is read
- **THEN** it MUST specify an exact pin pattern (`langgraph==…`) and MUST NOT leave `langgraph>=0.2.0` as the locked install line

### Requirement: REPLAN coarse-graining documented as intentional
Step 5.3 MUST document that REPLAN tools (`reoptimize_routes`, `expand_poi_search`) and `finish_plan` MAY perform multiple internal engine/search steps under one `execute_tool` call as intentional recovery coarse-graining. Sub-step timings, if needed, MUST go in `ToolResult.data` rather than synthetic extra `tool_trace` entries that inflate `tool_loop_count`.

#### Scenario: REPLAN multi-step under one execute_tool is allowed
- **WHEN** an implementer reads step 5.3 rationale
- **THEN** multi-step REPLAN under one registry call is described as deliberate, not as a violation of “nodes only call execute_tool”

### Requirement: Named constants and validate_itinerary field mapping in step5
`docs/steps/step5.md` MUST name `SEARCH_EXPAND_FACTOR = 1.5` and `RANK_EXPLANATION_TOP_N = 5` as named constants (planner tools constants or `travel_rules`), not inline magic literals. Step 5.3 MUST include an explicit field mapping from `state.route` / `state.schedule` into `travel_engine` `TripItinerary` / `DayPlan` for `validate_itinerary`.

#### Scenario: Expand factor is a named constant
- **WHEN** `expand_poi_search` behavior is specified in step 5.3
- **THEN** the 1.5 multiplier is referenced as `SEARCH_EXPAND_FACTOR` (or equivalent named constant), not only as a bare literal
