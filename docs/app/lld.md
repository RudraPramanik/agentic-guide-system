# Wandr Backend — Low-Level Design Patterns & Principles

> Every design decision is named explicitly. Patterns are introduced at the step that needs them.
> Full pattern inventory also lives in [`docs/blueprint_final.md`](../blueprint_final.md#lld-pattern-reference).

## Guiding Principles

| # | Principle | Implication |
|---|-----------|-------------|
| 1 | Packages at point of use | Nothing in `requirements.txt` until the step that needs it |
| 2 | LLD pattern named per step | Document the pattern when you introduce it |
| 3 | Failure boundary per step | Every external call has timeout, retry, and named fallback |
| 4 | Production abstracted from step 1 | Same code runs locally and in prod via env vars |
| 5 | Lightest viable package | No heavy deps without justification |
| 6 | Travel intelligence is first-class | `travel_engine/` is pure Python, separate from LangGraph |
| 7 | Evaluation from day one | Every generation and edit is recorded |
| 8 | LLM provider swappable | All LLM calls through `core/llm/client.py` only |
| 9 | Resilience mandatory | Explicit timeouts, tenacity retry, never raw 500 from externals |
| 10 | Controlled AI-assisted dev | `AGENT.md` guardrails govern all code |
| 11 | Structure from code, narrative from LLM | Geometry, order, times never from free-form LLM output |
| 12 | Tools are typed contracts | Pydantic schemas on every planner tool |
| 13 | Agent loops are bounded | `max_tool_calls`, phase gating, validate-before-finish |

## Layering Rules

```
Router  →  Service  →  Repository  →  Database
  │           │
  │           └── may call: travel_engine, planner/tools, geo, search, core/llm
  │
  └── returns ApiResponse[T] or PaginatedResponse[T] only
```

**Hard bans:**

- Router never touches DB directly
- No `litellm` / `openai` / `groq` imports outside `core/llm/client.py`
- No Nominatim / Overpass / OSRM calls outside `src/geo/`
- No planner side effects inline in LangGraph nodes — use `planner/tools/` or domain services
- No I/O inside `travel_engine/` — routing times injected via `RoutingProvider`

## Pattern Catalog

### Implemented (steps 0.1–0.4)

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Modular Monolith** | `src/` package layout | Single deployable unit, clear domain boundaries |
| **Configuration Object** | `src/config.py` | All env vars in one `Settings` class |
| **Singleton** | `get_settings()` | `@lru_cache` — parsed once per process |
| **Context Propagation** | `core/observability/logging.py` | `bind_contextvars()` flows `request_id` through all log lines without per-call passing |

#### Step 0.4 — Logging design detail

```python
# App lifespan (once)
configure_logging()

# Middleware (per request)
structlog.contextvars.bind_contextvars(request_id=request_id)

# Any layer
log = get_logger()
log.info("place_ranked", place_id=pid, score=score)
# → request_id appears automatically in output
```

Renderer selection reads `get_settings().ENVIRONMENT`:

- `"production"` → `JSONRenderer` (machine-parseable, ships to log aggregators)
- anything else → `ConsoleRenderer(colors=True)` (human-readable local dev)

`configure_logging()` is idempotent and falls back to `ConsoleRenderer` if settings are not yet loadable.

### Planned (upcoming steps)

| Pattern | Location | Step |
|---------|----------|------|
| **Null Object** | `NoOpTracer` in `core/observability/tracing.py` | 0.5 |
| **Gateway** | `core/llm/client.py` | 0.6 |
| **Strategy** | `chat_completion(model=...)`, `RoutingProvider` | 0.6, P4 |
| **Response Envelope** | `ApiResponse[T]`, `PaginatedResponse[T]` | 0.7–0.8 |
| **Exception Hierarchy** | `WandrError` tree | 0.9 |
| **App Factory** | `create_app()` in `main.py` | 0.10 |
| **Generic Repository** | `BaseRepository[M, ID]` | 1.2 |
| **Unit of Work** | Session per request | 1.2 |
| **Cache-Aside** | Destinations, planner cache | P2+ |
| **Protocol / DI** | `travel_engine` routing injection | P4 |
| **Tool Registry** | `planner/tools/registry.py` | P5 |
| **Phase-Gated Tool Loop** | `agent` ↔ `tool_executor` | P5 |
| **Bounded ReAct** | `tool_loop_count` ceiling | P5 |
| **Bookend Nodes** | `parse_preferences`, `write_narrative` outside loop | P5 |
| **State Machine** | `TravelState` through LangGraph | P5 |
| **Builder** | `build_graph()` | P5 |
| **Chain of Responsibility** | Middleware stack, validator rules | 0.10+, P4 |

## Resilience Contract (summary)

Every external call must have:

1. Explicit `connect_timeout` and `read_timeout` on httpx
2. Tenacity retry per the blueprint Resilience Contracts table
3. A named fallback — external failure never becomes a 500

See `AGENT.md` and blueprint for per-service timeout/retry values.

## Planner Agent Constraints

| Constraint | Mechanism |
|------------|-----------|
| Tool names | `TOOL_REGISTRY` only — agent never invents tools |
| Tool args | Validated against Pydantic input schema before execution |
| Execution path | `execute_tool(name, input, ctx)` — nodes never call impl directly |
| Phase gating | Agent binds only tools for `state.agent_phase` |
| Loop ceiling | `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → force WRAP_UP |
| Finish gate | `finish_plan` blocked until `validate_itinerary` ok or `abort_triggered` |
| Narrative | `write_narrative` runs outside tool loop as fixed post-loop node |
| Generation timeout | SSE wrapped in `asyncio.wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)` |
| Replan bound | `replan_loop_count < PLANNER_MAX_REPLAN_ATTEMPTS` before replan path |

## Evaluation Rule

`evaluation/` records **every** generation and **every** edit — including partial failures. Never skip.

## Constants Placement

| What | Where |
|------|-------|
| Env vars / tunables | `src/config.py` |
| Travel domain rules | `src/travel_engine/travel_rules.py` |
| Tool names, phase maps | `src/planner/tools/registry.py` |

No magic strings, numbers, or URLs elsewhere.
