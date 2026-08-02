## ADDED Requirements

### Requirement: HTTP SSE adapter consumes generate on_event without FastAPI types in service
`PlannerService.generate` MUST remain the HTTP-agnostic generation runner. The P6 FastAPI router MAY adapt it by supplying an `on_event` callback that enqueues events for a StreamingResponse generator and by running `generate` as a background task. The service module MUST NOT import FastAPI `Request` or `StreamingResponse`.

Existing contracts remain in force: fresh `ToolContext` per invoke, `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`, `last_known_state` on timeout, and evaluation persistence after return/timeout/clarification short-circuit.

#### Scenario: Service stays free of FastAPI streaming types
- **WHEN** `src/planner/service.py` is inspected for FastAPI streaming imports
- **THEN** it does not import `StreamingResponse` or depend on `Request.is_disconnected`

#### Scenario: Router can drive SSE from on_event
- **WHEN** the generate endpoint runs with an `on_event` that enqueues `(event, data)`
- **THEN** tool/phase events emitted during generation become available to the SSE generator before `generate` returns
