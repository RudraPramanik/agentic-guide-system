## MODIFIED Requirements

### Requirement: One trace per planner generation
Each `PlannerService.generate()` invocation SHALL produce at most one logical trace spanning the full lifecycle — including timeout and controlled-abort paths — containing child spans for tool executions (derived from recorded tool traces) and generation spans for LLM calls. The generation service MUST start that parent trace before the graph runs and MUST end it after evaluation recording (or after a synthetic timeout/abort final is built), so tool spans nest under the parent when tracing is active. Trace emission MUST NOT add synchronous blocking I/O to the generation critical path beyond what the SDK batches asynchronously. Tracer failures MUST remain fail-soft (never fail the generation).

#### Scenario: Successful generation yields complete trace
- **WHEN** a generation completes successfully and both Langfuse keys are configured
- **THEN** one parent trace exists covering start-to-evaluation-write with tool spans matching the tool trace entries nested under that parent and LLM generation spans for each gateway call

#### Scenario: Timeout still closes the trace
- **WHEN** a generation hits the generation timeout or recursion abort
- **THEN** the parent trace is ended with the terminal outcome recorded, not left dangling

#### Scenario: Empty keys keep generate behavior unchanged
- **WHEN** Langfuse keys are empty (NoOp path) and generate runs
- **THEN** the generation still completes and writes evaluation as today; no Langfuse network traffic occurs

#### Scenario: Tool spans require an active parent
- **WHEN** a successful generation has non-empty `tool_trace` entries and Langfuse keys are configured
- **THEN** tool spans are emitted under the parent generation trace (not silently skipped for lack of an active parent)
