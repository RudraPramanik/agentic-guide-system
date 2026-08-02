## Purpose

P5.12 PlannerService SSE bridge: `generate` with wait_for ceiling, last_known_state on timeout, always-eval after generate. P6 HTTP router adapts via `on_event` + background task; service stays free of FastAPI streaming types.

## Requirements

### Requirement: PlannerService.generate runs graph with wait_for ceiling
The project SHALL implement `PlannerService` in `src/planner/service.py` with
`async def generate(self, *, destination_id, raw_input, base_lat, base_lng, session_id, on_event: Callable[[str, dict], None] | None = None) -> TravelState` such that:

- It builds an initial `TravelState` and a **fresh** `ToolContext` (routing=`OsrmRoutingProvider()`, `db=None` unless a measured need) **per invoke** — never reuse ToolContext across generates.
- It obtains the graph via `get_compiled_graph()` (cached singleton) and passes
  `config={"configurable": {"tool_context": ctx, "emit": _capture_and_emit}}`.
- It MUST wrap `graph.ainvoke(...)` in `asyncio.wait_for(..., timeout=get_settings().PLANNER_GENERATION_TIMEOUT_SECONDS)`.
- It MUST NOT register FastAPI routes or StreamingResponse in this capability.

#### Scenario: generate source uses wait_for
- **WHEN** `PlannerService.generate` source is inspected
- **THEN** it contains `wait_for` and timeout comes from settings (not a hardcoded magic number unrelated to config)

#### Scenario: Fresh ToolContext per invoke
- **WHEN** two sequential or concurrent `generate` calls run against the same compiled graph
- **THEN** each invoke supplies its own `tool_context` via configurable (no compile-time ToolContext closure)

### Requirement: last_known_state survives generation timeout
`generate` SHALL keep a `last_known_state` dict **outside** the cancellable `wait_for` task. The configurable `emit` / `_capture_and_emit(event, data, state_snapshot=None)` MUST update that dict when `state_snapshot` is provided (`clear` + `update`). On `TimeoutError`:

- Final state MUST merge `last_known_state` with `errors` including `generation_timeout` and `abort_triggered=True`.
- It MUST emit an error event with code `generation_timeout` when `on_event` is set.
- It MUST NOT hang waiting for the cancelled graph task’s return value as the sole final state.

#### Scenario: Timeout yields controlled error state
- **WHEN** generation exceeds `PLANNER_GENERATION_TIMEOUT_SECONDS` after at least one emit checkpoint
- **THEN** returned state has `abort_triggered=True`, `errors` contain `generation_timeout`, and `tool_trace` reflects pre-timeout progress when snapshots were emitted

### Requirement: Service ensures evaluation after generate
After `ainvoke` returns or the timeout path builds `final`, `generate` MUST await evaluation persistence for `final` (call the existing `record_evaluation` node / evaluation path) so clarification and timeout short-circuits that skipped the graph eval node still produce a `TripEvaluation` row. DB failure MUST soft-fail (warning/log) without raising out of `generate`.

#### Scenario: Clarification or timeout still records evaluation
- **WHEN** generate finishes with `needs_clarification=True` or via the timeout path
- **THEN** evaluation persistence is invoked for the returned final state

### Requirement: HTTP SSE adapter consumes generate on_event without FastAPI types in service
`PlannerService.generate` MUST remain the HTTP-agnostic generation runner. The P6 FastAPI router MAY adapt it by supplying an `on_event` callback that enqueues events for a StreamingResponse generator and by running `generate` as a background task. The service module MUST NOT import FastAPI `Request` or `StreamingResponse`.

Existing contracts remain in force: fresh `ToolContext` per invoke, `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)`, `last_known_state` on timeout, and evaluation persistence after return/timeout/clarification short-circuit.

#### Scenario: Service stays free of FastAPI streaming types
- **WHEN** `src/planner/service.py` is inspected for FastAPI streaming imports
- **THEN** it does not import `StreamingResponse` or depend on `Request.is_disconnected`

#### Scenario: Router can drive SSE from on_event
- **WHEN** the generate endpoint runs with an `on_event` that enqueues `(event, data)`
- **THEN** tool/phase events emitted during generation become available to the SSE generator before `generate` returns
