## Purpose

P5.6 LangGraph planner state: serializable `TravelState` TypedDict and exact `langgraph` pin with configurable ToolContext hello-world check.

## Requirements

### Requirement: TravelState TypedDict with blueprint fields
The project SHALL provide `TravelState` as a TypedDict in `src/planner/graph/state.py` covering:

- Input: `destination_id`, `destination_name`, `destination_lat`, `destination_lng`, `raw_input`, `session_id`, `base_lat`, `base_lng`
- Prefs: `days`, `budget`, `interests`, `include_offbeat`, `include_trekking`
- Loop: `agent_phase`, `tool_loop_count`, `pending_tool_calls`, `tool_trace`, `plan_complete`, `needs_clarification`, `clarification_question`
- Resilience: `replan_loop_count`, `max_replan_attempts`, `abort_triggered`, `llm_retry_count`, `used_geo_fallback`, `used_osrm_fallback`, `readiness_score`
- Working: `candidate_pois`, `ranked_pois`, `route`, `schedule`, `itinerary`, `validation_result`
- Output: `errors`, `warnings`, `trace_id`

Values MUST prefer JSON-serializable types (UUID as `str` is allowed if used consistently). `max_replan_attempts` default MUST come from `get_settings().PLANNER_MAX_REPLAN_ATTEMPTS` at graph invoke time (not hardcoded in the TypedDict definition as a magic literal for runtime).

#### Scenario: TravelState type hints are importable
- **WHEN** `TravelState` is imported and `typing.get_type_hints(TravelState)` is inspected
- **THEN** the hint set includes the blueprint loop and resilience fields above and is non-empty

### Requirement: TravelState forbids I/O resources
`TravelState` MUST NOT declare fields for `db`, `routing`, `ToolContext`, `AsyncSession`, httpx clients, or other non-serializable request resources. Those live on `ToolContext` threaded via `config["configurable"]["tool_context"]` (implemented in later steps).

#### Scenario: No db or routing on TravelState
- **WHEN** type hints for `TravelState` are inspected
- **THEN** `"db"` and `"routing"` are absent from the hint keys

### Requirement: List fields are last-write-wins without Annotated reducers
List-shaped fields `tool_trace`, `warnings`, and `errors` MUST be documented and typed such that P5 nodes return the full extended list on each update. The implementation MUST NOT rely on LangGraph `Annotated` reducers for these fields in P5.

#### Scenario: No reducer dependency for tool_trace
- **WHEN** `TravelState` is defined for P5
- **THEN** list accumulation for `tool_trace` / `warnings` / `errors` is specified as full-list return (last-write-wins), not as an `Annotated` operator.add (or equivalent) reducer

### Requirement: Exact langgraph pin and configurable hello-world
`requirements.txt` MUST include an exact pin `langgraph==X.Y.Z` with a why-comment (P5.6 planner agent graph). Floating pins (`>=`) are FORBIDDEN.

Before the full planner graph is built (5.11), the project MUST verify a trivial two-node `StateGraph` with a conditional edge that passes `config={"configurable": {"tool_context": sentinel}}` and asserts the node received the sentinel from `config["configurable"]["tool_context"]`.

#### Scenario: langgraph imports after pin
- **WHEN** `langgraph` is imported after install
- **THEN** the import succeeds for the pinned version

#### Scenario: tool_context configurable round-trip
- **WHEN** the hello-world graph is ainvoked with a sentinel `tool_context` in configurable
- **THEN** a node observes that same sentinel from `config["configurable"]["tool_context"]`
