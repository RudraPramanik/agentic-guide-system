## MODIFIED Requirements

### Requirement: Fail-soft tracing facade with kill-switch
Tracing SHALL be active only when both Langfuse keys are configured; with default empty keys the system MUST behave byte-identically to the untraced implementation (no-op tracer, no network calls, no log noise beyond startup). When keys are configured, the tracer MUST honor an optional host setting (`LANGFUSE_HOST`, accepting the existing `LANGFUSE_BASE_URL` env alias) so Cloud EU/US and self-hosted deployments route correctly. Any tracer failure (construction, span creation, flush) MUST be swallowed and logged once per process without propagating to the caller.

#### Scenario: Unconfigured keys produce no behavior change
- **WHEN** `LANGFUSE_PUBLIC_KEY` or `LANGFUSE_SECRET_KEY` is empty (default)
- **THEN** generation results, latencies, and evaluation rows are identical to an untraced run and no Langfuse network traffic occurs

#### Scenario: Tracer failure never fails a generation
- **WHEN** the tracer raises during trace/span creation or flush mid-generation
- **THEN** the generation completes normally and the error is logged once

#### Scenario: Custom host is honored when keys are set
- **WHEN** both Langfuse keys are non-empty and `LANGFUSE_HOST` (or `LANGFUSE_BASE_URL`) is set to a non-default base URL
- **THEN** the Langfuse client is constructed targeting that host and traces are emitted there (not silently dropped to the wrong region)

### Requirement: One trace per planner generation
Each `PlannerService.generate()` invocation SHALL produce at most one logical trace spanning the full lifecycle — including timeout and controlled-abort paths — containing child spans for tool executions (derived from recorded tool traces) and generation observations for LLM calls. The generation service MUST start that parent trace before the graph runs and MUST finalize it after evaluation recording (or after a synthetic timeout/abort final is built) using the supported Langfuse v2 parent-trace API (`update` with terminal output/metadata; parent traces MUST NOT call a non-existent `end()` method). When tracing is active, `session_id` MUST be set as a first-class Langfuse trace field (not metadata-only), and `user_id` MUST be set when an authenticated user id is available on the generate call. Trace emission MUST NOT add synchronous blocking I/O to the generation critical path beyond what the SDK batches asynchronously. Tracer failures MUST remain fail-soft (never fail the generation).

#### Scenario: Successful generation yields complete trace
- **WHEN** a generation completes successfully and both Langfuse keys are configured
- **THEN** one parent trace exists covering start-to-evaluation-write with tool spans matching the tool trace entries nested under that parent and LLM generation observations for each gateway call, and the parent trace has a terminal output/metadata update (not left open)

#### Scenario: Timeout still closes the trace
- **WHEN** a generation hits the generation timeout or recursion abort
- **THEN** the parent trace is finalized with the terminal outcome recorded, not left dangling

#### Scenario: Empty keys keep generate behavior unchanged
- **WHEN** Langfuse keys are empty (NoOp path) and generate runs
- **THEN** the generation still completes and writes evaluation as today; no Langfuse network traffic occurs

#### Scenario: Tool spans require an active parent
- **WHEN** a successful generation has non-empty `tool_trace` entries and Langfuse keys are configured
- **THEN** tool spans are emitted under the parent generation trace (not silently skipped for lack of an active parent)

#### Scenario: Session groups traces in Langfuse UI
- **WHEN** a generate call includes a guest or authenticated session id and Langfuse keys are configured
- **THEN** the parent trace carries that value as Langfuse `session_id` so Sessions view can group related generations

## ADDED Requirements

### Requirement: LLM gateway uses Langfuse callback when tracing is active
When both Langfuse keys are configured and a parent generation trace is active, LLM gateway calls (`chat_completion`, `chat_with_tools`, `embed_texts`) SHALL emit Langfuse generation observations via the official LiteLLM callback integration (or equivalent supported v2 handler), capturing model name and token usage automatically. When keys are empty or no parent trace is active, the gateway MUST NOT register callbacks and MUST behave identically to today. Duplicate manual generation spans for the same call MUST NOT be emitted when the callback already records the observation.

#### Scenario: Active trace gets automatic LLM generations
- **WHEN** `PlannerService.generate()` runs with Langfuse keys set and the agent invokes `chat_with_tools`
- **THEN** Langfuse shows a generation observation under the parent trace with model and token fields populated without requiring duplicate manual span code for that call

#### Scenario: NoOp path skips callback registration
- **WHEN** Langfuse keys are empty
- **THEN** LiteLLM calls proceed with no Langfuse callbacks and no extra network I/O

### Requirement: Tracer flush on application shutdown
The FastAPI application lifespan SHALL call the tracer flush helper during shutdown so batched Langfuse events are delivered before the process exits (including dev reload and short CLI runs that call `flush_tracer()` explicitly).

#### Scenario: Shutdown delivers pending events
- **WHEN** the API process receives a shutdown signal after at least one traced generation
- **THEN** `flush_tracer()` runs once during lifespan teardown without raising to the caller

#### Scenario: Empty keys shutdown is a no-op
- **WHEN** Langfuse keys are empty and the API shuts down
- **THEN** shutdown flush completes without error and performs no network calls
