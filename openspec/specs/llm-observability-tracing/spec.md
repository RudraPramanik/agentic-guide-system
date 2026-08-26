## Purpose

Trace and token instrumentation of the LLM gateway and planner generation lifecycle via the existing NoOpTracer/Langfuse facade — fail-soft by contract, kill-switched by empty keys, so observability can never break a generation.

## Requirements

### Requirement: LLM gateway captures token usage
The LLM gateway functions (`chat_completion`, `chat_with_tools`, `embed_texts`) SHALL capture the provider response's usage data (prompt/completion/total tokens where available) and expose it on their return values without changing existing return contracts. When the provider returns no usage data, capture MUST degrade to an empty/zero-value result rather than raising.

#### Scenario: Usage captured from provider response
- **WHEN** a provider response includes usage data
- **THEN** the gateway's return value carries prompt, completion, and total token counts

#### Scenario: Missing usage degrades silently
- **WHEN** a provider response contains no usage object
- **THEN** the call succeeds with empty/zero token counts and no exception

### Requirement: Generation records token usage in evaluation
A completed planner generation SHALL record actual cumulative token usage and LLM retry count into its `TripEvaluation` row (columns already exist). Generations that make zero LLM calls MUST record empty/zero values, not nulls-from-never-written.

#### Scenario: Evaluation row reflects real tokens
- **WHEN** a generation completes after N successful LLM calls
- **THEN** the written `TripEvaluation` has `token_usage` summing across those calls and a non-zero `llm_retry_count` only if retries occurred

#### Scenario: Zero-LLM-call generation still writes valid evaluation
- **WHEN** a generation completes without any LLM call (e.g., fully cached or fallback path)
- **THEN** `token_usage` is written as an empty/zero value and the evaluation row is created

### Requirement: Fail-soft tracing facade with kill-switch
Tracing SHALL be active only when both Langfuse keys are configured; with default empty keys the system MUST behave byte-identically to the untraced implementation (no-op tracer, no network calls, no log noise beyond startup). Any tracer failure (construction, span creation, flush) MUST be swallowed and logged once per process without propagating to the caller.

#### Scenario: Unconfigured keys produce no behavior change
- **WHEN** `LANGFUSE_PUBLIC_KEY` or `LANGFUSE_SECRET_KEY` is empty (default)
- **THEN** generation results, latencies, and evaluation rows are identical to an untraced run and no Langfuse network traffic occurs

#### Scenario: Tracer failure never fails a generation
- **WHEN** the tracer raises during trace/span creation or flush mid-generation
- **THEN** the generation completes normally and the error is logged once

### Requirement: One trace per planner generation
Each `PlannerService.generate()` invocation SHALL produce at most one logical trace spanning the full lifecycle — including timeout and controlled-abort paths — containing child spans for tool executions (derived from recorded tool traces) and generation spans for LLM calls. Trace emission MUST NOT add synchronous blocking I/O to the generation critical path beyond what the SDK batches asynchronously.

#### Scenario: Successful generation yields complete trace
- **WHEN** a generation completes successfully
- **THEN** one trace exists covering start-to-evaluation-write with tool spans matching the tool trace entries and LLM generation spans for each gateway call

#### Scenario: Timeout still closes the trace
- **WHEN** a generation hits the generation timeout or recursion abort
- **THEN** the trace is ended with the terminal outcome recorded, not left dangling
