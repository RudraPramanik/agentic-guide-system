## ADDED Requirements

### Requirement: Reasoning side work cannot consume the graph timeout
`PlannerService.generate` MUST keep `graph.ainvoke` inside `asyncio.wait_for` with `PLANNER_GENERATION_TIMEOUT_SECONDS`. Shadow sampling and the advisory critic MUST run only after that wait has returned a final state and after the terminal event has been emitted. They MUST NOT be inside that wait. A failure or deadline in that side work MUST NOT change a successful graph result into `generation_timeout` or `abort_triggered`. The service module MUST still not import FastAPI streaming types.

When `REASONING_LAYER_ENABLED` is false and the request is not sampled, `generate` MUST NOT call the reasoner or the critic. Evaluation persistence MUST still run for the control state.

#### Scenario: Graph timeout behavior is unchanged
- **WHEN** `graph.ainvoke` exceeds `PLANNER_GENERATION_TIMEOUT_SECONDS`
- **THEN** the returned state has `generation_timeout` and `abort_triggered` as it does today, and no reasoning call is required on that path

#### Scenario: Side-work timeout is not a generation timeout
- **WHEN** the graph returns `plan_complete` and a later critic call exceeds its own deadline
- **THEN** the state returned for save still has the graph's `plan_complete` result and does not gain `generation_timeout` from the critic

#### Scenario: Flags off make no reasoning call
- **WHEN** `REASONING_LAYER_ENABLED` is false and `REASONING_SHADOW_SAMPLE_RATE` is 0
- **THEN** `generate` does not call the reasoner or the critic
