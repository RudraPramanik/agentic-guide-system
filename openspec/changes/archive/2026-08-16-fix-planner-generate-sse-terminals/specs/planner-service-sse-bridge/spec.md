## ADDED Requirements

### Requirement: generate emit bridge publishes terminals after graph return
`PlannerService.generate` MUST, after `graph.ainvoke` returns a final state (and after the timeout/recursion paths build their final state), ensure `on_event` receives exactly one terminal event according to the locked precedence in `planner-sse-generate` (skip if a timeout/recursion `error` was already emitted). Emitting MUST use the existing `_capture_and_emit` / `emit` configurable hook so the HTTP adapter can buffer terminals unchanged.

The service MUST remain free of FastAPI `Request` / `StreamingResponse` types.

#### Scenario: Successful ainvoke emits itinerary_done via on_event
- **WHEN** `generate` is invoked with an `on_event` callback and the graph returns `plan_complete` with a usable schedule
- **THEN** `on_event` is called with `itinerary_done` before `generate` returns

#### Scenario: Clarification ainvoke emits clarification_needed via on_event
- **WHEN** `generate` returns with `needs_clarification=true`
- **THEN** `on_event` is called with `clarification_needed` and no `itinerary_done`

### Requirement: Bookend and phase progress emits on cold generate
`generate` (via nodes or the service emit bridge) MUST emit `preferences_done` after preference resolution and `phase_changed` when `agent_phase` changes, using the same `emit` configurable. These MUST update `last_known_state` when a state snapshot is provided.

#### Scenario: preferences_done emitted after parse bookend
- **WHEN** parse preferences completes (LLM or defaults)
- **THEN** `on_event` receives `preferences_done` with the resolved preference fields

## MODIFIED Requirements

### Requirement: HTTP SSE adapter consumes generate on_event without FastAPI types in service
`PlannerService.generate` MUST remain the HTTP-agnostic generation runner. The P6 FastAPI router MUST adapt it by supplying an `on_event` callback that enqueues events for a StreamingResponse generator and by running `generate` as a background task. The service module MUST NOT import FastAPI `Request` or `StreamingResponse`, and MUST NOT call `request.is_disconnected`.

Existing contracts remain in force: fresh `ToolContext` per invoke, `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`, `last_known_state` on timeout, and evaluation persistence after return/timeout/clarification short-circuit.

The service emit bridge MUST publish terminal outcomes (`itinerary_done`, `clarification_needed`, `error`) for cold generates so the router is not dependent on cache replay for success/clarification terminals. Step **6.2** owns the router-side SSE adapter; this requirement forbids moving StreamingResponse or disconnect checks into `src/planner/service.py`.

#### Scenario: Service stays free of FastAPI streaming types
- **WHEN** `src/planner/service.py` is inspected for FastAPI streaming imports
- **THEN** it does not import `StreamingResponse` or depend on `Request.is_disconnected`

#### Scenario: Router can drive SSE from on_event
- **WHEN** the generate endpoint runs with an `on_event` that enqueues `(event, data)`
- **THEN** tool/phase events emitted during generation become available to the SSE generator before `generate` returns

#### Scenario: Six-two validation finds no StreamingResponse in service
- **WHEN** step 6.2 import-guard validation scans `src/planner/service.py`
- **THEN** there are zero matches for `StreamingResponse` or `is_disconnected`

#### Scenario: Cold success terminal reaches on_event without cache replay
- **WHEN** a cold `generate` completes successfully with `on_event` set
- **THEN** `on_event` receives `itinerary_done` without invoking `_replay_cached`
