
- Router calls Service only. Service calls Repository only. Router never touches DB directly.
- LLM calls happen ONLY through `src/core/llm/client.py`. Never import litellm, groq, or openai directly anywhere else.
- Geo calls happen ONLY through `src/geo/`. Never call Nominatim, Overpass, or OSRM directly outside this module.
- Planner side effects (search, routing, DB) happen ONLY through `src/planner/tools/` or domain services — never inline in nodes.
- `travel_engine/` has NO LLM calls and NO network/DB I/O. Pure Python only. Routing times are injected via `RoutingProvider` from caller.
- `evaluation/` records every generation and every edit. Never skip this, even on partial failures.

### Resilience (non-negotiable)
- Every httpx call MUST have explicit connect_timeout and read_timeout set.
- Every external call MUST use tenacity retry. See Resilience Contracts table in blueprint.
- Every external call MUST have a named fallback. Never let an external failure raise a 500.
- LangGraph replan loop MUST check `replan_loop_count < max_replan_attempts` before entering replan path.
- The SSE stream MUST be wrapped in asyncio.wait_for with PLANNER_GENERATION_TIMEOUT_SECONDS ceiling (default 45s).

### Agent / tools (non-negotiable)
- Agent tool calls MUST use names from `TOOL_REGISTRY` only — never invent tools.
- Tool args MUST validate against the tool's Pydantic input schema before execution.
- All tool execution goes through `execute_tool(name, input, ctx)` — agent node never calls impl functions directly.
- `finish_plan` MUST NOT succeed until `validate_itinerary` returned `ok=True` OR `state.abort_triggered=True`.
- LLM never outputs place IDs, coordinates, stop order, or times — those come from travel_engine + tools only.
- Phase gating: agent node binds ONLY tools allowed for `state.agent_phase` — never expose full registry to LLM.
- On `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → force transition to WRAP_UP phase.
- Narrative (`write_narrative`) runs OUTSIDE the tool loop — fixed node after agent loop completes.

### Code conventions
- All env var access through `get_settings()`. Never `os.environ.get()` directly.
- Every new endpoint returns `ApiResponse[T]` or `PaginatedResponse[T]`. Never a raw dict.
- No new packages without appending to requirements.txt with a comment explaining why.
- No hardcoded strings, numbers, or URLs. All constants in `travel_rules.py` or `config.py`.

### When in doubt
- Check the Resilience Contracts table before adding any external call.
- If a node needs to call an LLM, go through `core/llm/client.py` — no exceptions.
- If unsure about a timeout value, use the value from the Resilience Contracts table.
---