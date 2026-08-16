## MODIFIED Requirements

### Requirement: PlannerService.generate runs graph with wait_for ceiling
The project SHALL implement `PlannerService` in `src/planner/service.py` with
`async def generate(self, *, destination_id, raw_input, base_lat, base_lng, session_id, on_event: Callable[[str, dict], None] | None = None) -> TravelState` such that:

- It builds an initial `TravelState` and a **fresh** `ToolContext` (routing=`get_routing_provider()` unless the caller injects a test Fake, `db=None` unless a measured need) **per invoke** — never reuse ToolContext across generates.
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

#### Scenario: Default routing comes from factory
- **WHEN** `generate` is called without an injected routing adapter
- **THEN** `ToolContext.routing` is the adapter returned by `get_routing_provider()`
