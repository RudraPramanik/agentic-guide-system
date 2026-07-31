## ADDED Requirements

### Requirement: Compiled planner graph with locked edges
The project SHALL implement `build_planner_graph()` / `get_compiled_graph()` in `src/planner/graph/builder.py` that compiles a LangGraph with:

- `parse_preferences` → `agent`
- `agent` → `tool_executor` **unconditionally** every cycle
- After `tool_executor`, conditional:
  - `needs_clarification` → END
  - `plan_complete` → `write_narrative` → `record_evaluation` → END
  - else → `agent`

There MUST be no orphan nodes. Compilation MUST use the already-pinned `langgraph` dependency. The compiled graph MUST be cached as a process singleton (`get_compiled_graph`). Compilation failure MUST raise loudly at import/startup (not silently skip nodes).

Nodes MUST obtain `ToolContext` only at invoke time via `config["configurable"]["tool_context"]` — never via closure or module-global bound at compile time.

#### Scenario: Graph compiles
- **WHEN** `build_planner_graph()` is called
- **THEN** it returns a compiled graph object without error

#### Scenario: Agent always edges to tool_executor
- **WHEN** the compiled graph topology is inspected
- **THEN** every `agent` completion transitions to `tool_executor` with no conditional skip of the executor

#### Scenario: Plan-complete bookends outside the loop
- **WHEN** `plan_complete` is true after `tool_executor`
- **THEN** the path is `write_narrative` then `record_evaluation` then END (narrative/eval are not inside the agent↔executor loop)
