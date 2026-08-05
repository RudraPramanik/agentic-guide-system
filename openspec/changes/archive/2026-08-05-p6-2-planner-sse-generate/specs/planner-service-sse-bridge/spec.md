## MODIFIED Requirements

### Requirement: HTTP SSE adapter consumes generate on_event without FastAPI types in service
`PlannerService.generate` MUST remain the HTTP-agnostic generation runner. The P6 FastAPI router MUST adapt it by supplying an `on_event` callback that enqueues events for a StreamingResponse generator and by running `generate` as a background task. The service module MUST NOT import FastAPI `Request` or `StreamingResponse`, and MUST NOT call `request.is_disconnected`.

Existing contracts remain in force: fresh `ToolContext` per invoke, `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`, `last_known_state` on timeout, and evaluation persistence after return/timeout/clarification short-circuit.

Step **6.2** MUST land the router-side SSE adapter; this requirement forbids moving StreamingResponse or disconnect checks into `src/planner/service.py`.

#### Scenario: Service stays free of FastAPI streaming types
- **WHEN** `src/planner/service.py` is inspected for FastAPI streaming imports
- **THEN** it does not import `StreamingResponse` or depend on `Request.is_disconnected`

#### Scenario: Router can drive SSE from on_event
- **WHEN** the generate endpoint runs with an `on_event` that enqueues `(event, data)`
- **THEN** tool/phase events emitted during generation become available to the SSE generator before `generate` returns

#### Scenario: Six-two validation finds no StreamingResponse in service
- **WHEN** step 6.2 import-guard validation scans `src/planner/service.py`
- **THEN** there are zero matches for `StreamingResponse` or `is_disconnected`
