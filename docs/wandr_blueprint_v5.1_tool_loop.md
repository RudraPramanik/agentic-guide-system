# Wandr — Backend Blueprint v5.1 (Phase-Gated Tool Loop Agent)
> Extends `wandr_blueprint_v5.md` with a **bounded tool-loop agent** while preserving all v5 principles, resilience contracts, and controlled output rules.

**Base document:** `wandr_blueprint_v5.md` (unchanged)  
**This document replaces:** v5 § Controlled Agent Graph, v5 § P5, and v5 AGENT.md agent/tool rules  
**Everything else in v5 (P0–P4, P6–P7, travel_engine, tools impl, edit APIs) applies as written.**

---

## What's new in v5.1

| Area | v5 | v5.1 |
|------|----|------|
| Orchestration | Fixed pipeline nodes + replan supervisor enum | **Phase-gated tool loop** — LLM picks next tool from allowlist per phase |
| Agent node | Separate nodes per step | **`agent` + `tool_executor`** loop until `finish_plan` or ceiling hit |
| LLM client | `chat_completion()` only | + **`chat_with_tools()`** — still only entry point for LiteLLM |
| Loop ceiling | `replan_loop_count` on validation replans only | **`tool_loop_count`** on every tool call + **`replan_loop_count`** on REPLAN phase |
| Terminal tools | `ReplanAction` enum via supervisor | **`finish_plan`**, **`ask_clarification`** as registered tools with preconditions |
| Eval | `replan_actions_taken` | + **`tool_trace`** — full auditable log of every tool invocation |
| SSE | Fixed milestone events | + **`tool_started` / `tool_done`** per tool call |
| P5 timeline | 6 days | **7 days** |

**Unchanged:** Principles 1–12, `travel_engine` purity, `execute_tool()` gateway, itinerary schema, P7 edit APIs, readiness, schedule_builder.

---

## Principle 13 (add to v5 table)

| # | Principle |
|---|-----------|
| 13 | **Agent loops are bounded** — every tool-loop run has `max_tool_calls`, phase gating, and validate-before-finish; no unbounded ReAct |

---

## AGENT.md — Agent / Tools section (replace v5 block)

```markdown
### Agent / tools (non-negotiable)
- Agent tool calls MUST use names from `TOOL_REGISTRY` only — never invent tools.
- Tool args MUST validate against the tool's Pydantic input schema before execution.
- All tool execution goes through `execute_tool(name, input, ctx)` — agent node never calls impl functions directly.
- `finish_plan` MUST NOT succeed until `validate_itinerary` returned `ok=True` OR `state.abort_triggered=True`.
- LLM never outputs place IDs, coordinates, stop order, or times — those come from travel_engine + tools only.
- Phase gating: agent node binds ONLY tools allowed for `state.agent_phase` — never expose full registry to LLM.
- On `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → force transition to WRAP_UP phase (validate → narrative → finish).
- Narrative (`write_narrative`) runs OUTSIDE the tool loop — fixed node after agent loop completes.
```

---

## Environment Variables (add to v5 Settings)

```bash
PLANNER_MAX_TOOL_CALLS=12              # hard ceiling — every execute_tool increments tool_loop_count
PLANNER_AGENT_PHASE_STUCK_LIMIT=3      # same phase with no state change → auto-advance or abort
```

All other v5 planner env vars unchanged (`PLANNER_MAX_REPLAN_ATTEMPTS`, `PLANNER_GENERATION_TIMEOUT_SECONDS`, etc.).

---

## core/llm/client.py — `chat_with_tools()` (v5.1)

> Still the **only** file that imports `litellm`. Extends v5 design — does not replace `chat_completion()`.

```python
@retry(...)  # same contract as chat_completion
async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],           # OpenAI-style tool schemas from registry.get_tool_schemas(phase)
    tool_choice: str = "auto",   # "auto" | "required" | "none"
    model: str | None = None,
) -> LLMToolResponse:
    """
    Returns LLMToolResponse with either:
      - tool_calls: list[{name, arguments_json}]
      - content: str (if model responded without tools)
    Raises WandrLLMError after retries exhausted.
    """
```

**Rules:**
- Tool schemas generated from Pydantic models in `planner/tools/schemas.py` — never hand-written JSON in nodes.
- Agent node passes **phase-filtered** schemas only.
- Preference parsing and narrative writing continue to use `chat_completion()` — not the tool loop.

---

## Tool Registry (v5.1 — extends v5 six tools)

### Core planning tools (unchanged from v5)
| Tool | Phase | Preconditions |
|------|-------|---------------|
| `check_readiness` | DISCOVER | — |
| `search_places` | DISCOVER | preferences parsed |
| `rank_places` | DISCOVER | `candidate_pois` non-empty |
| `build_route` | PLAN | `ranked_pois` non-empty |
| `build_schedule` | PLAN | `route` non-empty |
| `validate_itinerary` | VALIDATE | `schedule` or `route` non-empty |

### Agent control tools (v5.1 new)
| Tool | Phase | Behavior |
|------|-------|----------|
| `finish_plan` | WRAP_UP | Sets `state.plan_complete=True`; only if last validation ok OR `abort_triggered` |
| `ask_clarification` | DISCOVER | Sets `needs_clarification=True`, question string; SSE `clarification_needed`; ends loop early |

### Replan tools (v5.1 — replaces ReplanAction enum supervisor)
| Tool | Phase | Behavior |
|------|-------|----------|
| `reoptimize_routes` | REPLAN | Re-runs `build_route` + `build_schedule` for all days |
| `drop_weakest_stop` | REPLAN | Removes lowest-scored stop on worst day, re-runs route + schedule |
| `expand_poi_search` | REPLAN | Increases search top_k by 50%, re-runs search → rank → route → schedule |
| `accept_partial` | REPLAN | Sets `abort_triggered=True`, moves to WRAP_UP |

```python
TOOL_REGISTRY: dict[str, ToolDefinition] = {
    # ... all tools with: fn, input_model, output_model, allowed_phases, preconditions
}

def get_tools_for_phase(phase: AgentPhase) -> list[dict]:
    """OpenAI function schemas for LiteLLM — filtered by phase."""

async def execute_tool(name: str, input: BaseModel, ctx: ToolContext) -> ToolResult:
    # 1. Validate name in registry
    # 2. Validate phase allows tool
    # 3. Check preconditions against state → ToolResult(ok=False, code="precondition_failed") if fail
    # 4. Run tool fn inside try/except → never raise
    # 5. Append to state.tool_trace
    # 6. Increment state.tool_loop_count
    # 7. Return ToolResult
```

---

## Agent Phases

```python
class AgentPhase(str, Enum):
    DISCOVER = "discover"     # readiness, search, rank
    PLAN = "plan"             # build_route, build_schedule
    VALIDATE = "validate"     # validate_itinerary only (+ auto-advance on pass)
    REPLAN = "replan"         # replan tools — entered when validation fails
    WRAP_UP = "wrap_up"       # finish_plan only (agent loop exits → write_narrative node)
```

### Phase transitions (deterministic — not LLM-chosen)

| From | Condition | To |
|------|-----------|-----|
| DISCOVER | `rank_places` succeeded | PLAN |
| PLAN | `build_schedule` succeeded | VALIDATE |
| VALIDATE | `validate_itinerary` ok=True | WRAP_UP |
| VALIDATE | errors AND `replan_loop_count < max` | REPLAN |
| VALIDATE | errors AND replan exhausted | WRAP_UP (`abort_triggered=True`) |
| REPLAN | any replan tool succeeded | PLAN (re-validate next loop) |
| REPLAN | `accept_partial` OR replan max hit | WRAP_UP |
| Any | `tool_loop_count >= max` | WRAP_UP (`abort_triggered=True`) |
| DISCOVER | `ask_clarification` called | END (needs_input) |

### Tools exposed to LLM per phase

```python
PHASE_TOOLS = {
    AgentPhase.DISCOVER:  ["check_readiness", "search_places", "rank_places", "ask_clarification"],
    AgentPhase.PLAN:      ["build_route", "build_schedule"],
    AgentPhase.VALIDATE:  ["validate_itinerary"],
    AgentPhase.REPLAN:    ["reoptimize_routes", "drop_weakest_stop", "expand_poi_search", "accept_partial"],
    AgentPhase.WRAP_UP:   ["finish_plan"],
}
```

---

## LangGraph — Phase-Gated Tool Loop

```
START
  → parse_preferences          # single chat_completion — NOT in tool loop
  → agent                      # chat_with_tools — picks one tool from PHASE_TOOLS[phase]
  → tool_executor              # execute_tool — updates state, checks phase transition
  → [plan_complete OR needs_clarification OR abort?]
        needs_clarification → END
        plan_complete       → write_narrative → record_evaluation → END
        else                → agent (loop)
```

**Removed vs v5:** separate nodes `readiness_check`, `poi_retrieval`, `ranking`, `route_planner`, `schedule_builder`, `replan_supervisor` — all replaced by agent + tool_executor loop.

**Kept as fixed nodes (outside loop):**
- `parse_preferences` — one LLM JSON call, deterministic defaults on failure
- `write_narrative` — one LLM call; **cannot modify** stops/times/order
- `record_evaluation` — always runs

### planner/graph/nodes/agent.py
```python
async def agent_node(state: TravelState, ctx: ToolContext) -> TravelState:
    if state.tool_loop_count >= settings.PLANNER_MAX_TOOL_CALLS:
        state.abort_triggered = True
        state.agent_phase = AgentPhase.WRAP_UP
        return state

    tools = get_tools_for_phase(state.agent_phase)
    response = await chat_with_tools(
        messages=build_agent_messages(state),
        tools=tools,
    )

    if response.tool_calls:
        state.pending_tool_calls = response.tool_calls  # executor node consumes
    else:
        # Model replied without tool — nudge retry once, then deterministic default tool for phase
        state.warnings.append("agent_no_tool_call")
    return state
```

### planner/graph/nodes/tool_executor.py
```python
async def tool_executor_node(state: TravelState, ctx: ToolContext) -> TravelState:
    for call in state.pending_tool_calls:
        input_model = parse_tool_input(call.name, call.arguments_json)  # Pydantic
        result = await execute_tool(call.name, input_model, ctx)
        apply_tool_result(state, result)
        maybe_transition_phase(state, call.name, result)
    state.pending_tool_calls = []
    return state
```

### Deterministic fallback when agent misbehaves
| Situation | Fallback |
|-----------|----------|
| No tool call after nudge | Call default tool for current phase (e.g. DISCOVER → `check_readiness`) |
| Invalid tool for phase | Ignore; return `ToolResult(precondition_failed)` to agent message history |
| `WandrLLMError` in agent | Execute default tool chain for phase once; increment `llm_retry_count` |
| Same phase, no state change × 3 | Auto-advance phase OR `abort_triggered` |

---

## TravelState (v5.1 — extends v5)

```python
# Agent loop (v5.1)
agent_phase: AgentPhase = AgentPhase.DISCOVER
tool_loop_count: int = 0
pending_tool_calls: list[PendingToolCall] = []
tool_trace: list[ToolTraceEntry] = []   # {name, ok, ms, phase, code?, fallback_used?}
plan_complete: bool = False
needs_clarification: bool = False
clarification_question: str | None = None

# Retained from v5
replan_loop_count: int = 0            # increments on REPLAN phase entry only
max_replan_attempts: int
abort_triggered: bool = False
llm_retry_count: int = 0
used_geo_fallback: bool = False
used_osrm_fallback: bool = False
readiness_score: float | None = None
base_lat: float
base_lng: float

# Working data (tools read/write via typed helpers)
candidate_pois: list
ranked_pois: list
route: list
schedule: list
itinerary: dict                       # populated in write_narrative from schedule + route
validation_result: ValidationResult | None
```

**Removed from v5:** `replan_actions_taken` → replaced by `tool_trace` (strict superset).

---

## write_narrative node (fixed — outside tool loop)

- Input: locked `state.schedule` + `state.route` — structure is final
- Calls `chat_completion()` with prompt: day titles + paragraph per day only
- Output merged into `state.itinerary` without altering `ItineraryStop` fields
- Post-check: every `place_id` in narrative prompt must exist in schedule — LLM cannot add stops
- On `WandrLLMError`: template strings per day; increment `llm_retry_count`

---

## SSE Events (v5.1 — extends v5 sequence)

```
event: preferences_done     data: {...}                    # from parse_preferences (before loop)
event: phase_changed        data: {"phase":"plan"}         # on deterministic phase transition
event: tool_started         data: {"tool":"search_places","loop":2,"phase":"discover"}
event: tool_done            data: {"tool":"search_places","ok":true,"ms":340,"count":36}
event: clarification_needed data: {"question":"How many days?"}   # if ask_clarification
event: validation_done      data: {"passed":false,"errors":[...]} # after validate_itinerary
event: itinerary_done       data: {full ItineraryDay[] JSON}      # after write_narrative
event: error                data: {"code":"generation_timeout"}
```

**Deprecated vs v5 milestone events:** `readiness_done`, `pois_found`, `route_ready`, `schedule_ready`, `replan_started` — replaced by `tool_*` + `phase_changed`. Frontend can map tools to UI labels.

---

## evaluation — v5.1 additions

TripEvaluation adds / replaces:
```python
tool_loop_count: int
tool_trace: list[dict]              # serialized ToolTraceEntry[]
agent_phase_reached: str            # last phase before finish/abort
# remove: replan_actions_taken — data lives in tool_trace
```

Quality signals:
- High `tool_loop_count` near ceiling → agent struggling; tighten prompts or phase defaults
- Repeated `precondition_failed` in trace → agent prompt or phase tool list bug
- `expand_poi_search` in trace often → destination data or ranking issue

---

## Resilience Contracts (v5.1 additions)

| Component | Retry | Timeouts | Final Fallback |
|-----------|-------|----------|----------------|
| `agent` node (`chat_with_tools`) | via `core/llm/client.py` | `LLM_TIMEOUT_SECONDS` | default tool for phase; then `abort_triggered` |
| Tool loop (total) | no graph-level retry | bounded by `PLANNER_MAX_TOOL_CALLS` | force WRAP_UP → partial itinerary |
| `tool_executor` | inherits per-tool | — | `ToolResult(ok=False)` — never raises |
| Phase stuck detector | N/A | 3 iterations | auto-advance or WRAP_UP |

All v5 resilience rows unchanged for geo, OSRM, Qdrant, SSE timeout, etc.

---

## Project Structure (v5.1 graph changes)

```
planner/
├── graph/
│   ├── state.py
│   ├── builder.py              # agent ↔ tool_executor loop + fixed bookend nodes
│   ├── messages.py             # build_agent_messages — system prompt + tool results history
│   └── nodes/
│       ├── parse_preferences.py
│       ├── agent.py              # ★ LLM tool selection
│       ├── tool_executor.py      # ★ execute_tool + phase transitions
│       ├── write_narrative.py    # fixed LLM — outside loop
│       └── record_evaluation.py
├── tools/
│   ├── registry.py             # + get_tools_for_phase, precondition checks
│   ├── schemas.py              # + finish_plan, ask_clarification, replan tool I/O
│   ├── finish_plan.py
│   ├── ask_clarification.py
│   ├── reoptimize_routes.py
│   ├── drop_weakest_stop.py
│   ├── expand_poi_search.py
│   └── accept_partial.py
```

---

## P5 — Phase-Gated Tool Loop Agent (replaces v5 P5)
**7 days · 14 steps**

> Complete v5 steps 5.1–5.3 (tool impl) first — agent loop orchestrates existing tools.

#### 5.1 planner/tools/schemas.py + registry.py (v5 — unchanged)
#### 5.2 Implement core six tools (v5 — unchanged)
#### 5.3 Implement replan + control tools (v5.1)
- `finish_plan`, `ask_clarification`, `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, `accept_partial`
- Each: Pydantic I/O, phase tag, precondition function
- ✅ `finish_plan` without prior validate → `precondition_failed`

#### 5.4 core/llm/client.py — `chat_with_tools()` (v5.1)
- Schema passthrough to LiteLLM `acompletion(tools=...)`
- Parse `tool_calls` from response; handle model returning content-only
- 🔒 Same retry contract as `chat_completion`
- ✅ Mock LiteLLM response with tool_call → parsed correctly

#### 5.5 registry — phase gating + preconditions (v5.1)
- `get_tools_for_phase()`, `check_preconditions()`, `maybe_transition_phase()`
- `execute_tool` appends to `tool_trace`, increments `tool_loop_count`
- ✅ Wrong-phase tool rejected without execution

#### 5.6 planner/graph/state.py (v5.1 fields)
- Full TravelState per v5.1 spec
- ✅ TypedDict complete

#### 5.7 planner/graph/messages.py — agent prompt (v5.1)
- System prompt: role, allowed tools for current phase, hard rules (never invent places)
- Include compact state summary: days, interests, counts, last validation errors
- Include last 5 `tool_trace` entries as context — not full history (token control)

#### 5.8 nodes/parse_preferences.py (v5.1)
- Extract from v5 preference node — runs before loop
- ✅ Same behavior as v5 5.7 preference step

#### 5.9 nodes/agent.py + tool_executor.py (v5.1)
- Wire loop per graph diagram
- Deterministic fallbacks for no-tool-call and WandrLLMError
- ✅ DISCOVER → PLAN → VALIDATE → WRAP_UP on happy path

#### 5.10 nodes/write_narrative.py + record_evaluation.py (v5.1)
- write_narrative: locked structure, template fallback
- record_evaluation: persists `tool_trace`, `tool_loop_count`, all v5 eval fields
- ✅ Evaluation row includes full tool_trace JSON

#### 5.11 planner/graph/builder.py (v5.1)
- Compile graph; validate at startup
- Conditional: `plan_complete` → write_narrative; `needs_clarification` → END
- ✅ Graph compiles; no orphan nodes

#### 5.12 planner/service.py — SSE bridge (v5.1)
- Map `execute_tool` hooks to emit `tool_started` / `tool_done`
- Map phase transitions to `phase_changed`
- 🔒 Still wrapped in `asyncio.wait_for(..., PLANNER_GENERATION_TIMEOUT_SECONDS)`

#### 5.13 tests/planner/test_tool_loop.py (v5.1)
- Happy path: tool_loop_count ≤ 8, plan_complete, all stops timed
- Validation fail → REPLAN tools invoked → replan_loop_count ≤ max
- Max tool calls → abort_triggered, partial itinerary, evaluation recorded
- ask_clarification → needs_clarification, loop exits early
- ✅ pytest green

#### 5.14 scripts/test_agent.py (v5.1)
- End-to-end Darjeeling generation via HTTP or direct graph invoke
- Print tool_trace summary table to stdout
- ✅ Same assertions as v5 5.12 + tool_trace non-empty

---

## P6 — Updates for v5.1 (delta only)

#### 6.2 planner/router.py
- SSE: emit `tool_started`, `tool_done`, `phase_changed` instead of v5 milestone events
- Keep `preferences_done`, `itinerary_done`, `error`, `clarification_needed`

#### 6.5 ship checklist (additions)
- [ ] Agent never calls a tool outside current phase (integration test asserts)
- [ ] `finish_plan` blocked until validate ok or abort (unit test)
- [ ] `tool_trace` persisted on every generation
- [ ] Happy path: `tool_loop_count` ≤ 8, `abort_triggered=False`
- [ ] Kill LLM during agent loop → default tool fallback → itinerary or clean error event
- [ ] No `litellm` import outside `core/llm/client.py` (grep)
- [ ] grep: no direct tool fn imports in `planner/graph/nodes/` — only `execute_tool`

**P7 unchanged** — edit/replan uses tools directly via service layer, not agent loop.

---

## LLD Patterns (add to v5 table)

| Pattern | Where used |
|---------|------------|
| Phase-Gated Tool Loop | `agent` ↔ `tool_executor` with `PHASE_TOOLS` |
| Bounded ReAct | `tool_loop_count` + `PLANNER_MAX_TOOL_CALLS` |
| Tool Precondition | `registry.check_preconditions()` before every execute |
| Bookend Nodes | `parse_preferences` + `write_narrative` outside loop |

---

## Failure Boundary (v5.1 additions)

| Layer | Failure | Response |
|-------|---------|----------|
| Agent picks invalid tool name | Not in registry | Skip call; add to agent message history as error |
| Agent picks wrong-phase tool | Phase mismatch | `precondition_failed`; not executed |
| Agent no tool call | After nudge | Default tool for phase |
| `tool_loop_count >= max` | Ceiling hit | `abort_triggered`, WRAP_UP, partial plan |
| Phase stuck × 3 | No progress | Auto-advance or abort |
| `finish_plan` early | Validate not passed | `precondition_failed`; remain in loop |

---

## Timeline (v5.1)

| Phase | Days | Notes |
|-------|------|-------|
| P0–P4 | 17 | Same as v5 |
| P5 | **7** | +1 day vs v5 (tool loop agent) |
| P6–P7 | 5 | Same as v5, minor SSE checklist |
| **Total** | **~29 days** | Backend only |

---

## Implementation Order Recommendation

1. Build v5 tools (P5.1–5.3) and test in isolation — **no agent yet**
2. Add `chat_with_tools()` + phase registry
3. Wire agent loop with **deterministic phase transitions** first, LLM tool choice second
4. Add fallbacks and ceilings
5. Connect SSE + evaluation
6. Delete v5 hybrid nodes only after tool loop tests pass

---

## v5 → v5.1 Migration (for implementers)

1. If you started v5 hybrid graph — stop before `replan_supervisor.py`; switch to v5.1 graph.
2. `replan_actions_taken` → use `tool_trace` instead.
3. SSE clients: map `tool_done` events to UI progress (frontend blueprint).
4. Keep `travel_engine/`, P7, readiness, and resilience tables from v5 verbatim.

---

## Quick Reference: What the LLM can and cannot do

| Can | Cannot |
|-----|--------|
| Choose next tool from phase allowlist | Invent tool names or args outside schema |
| Call `ask_clarification` when input ambiguous | Output place IDs, lat/lng, or stop order |
| Call replan tools when validation fails | Skip `validate_itinerary` before `finish_plan` |
| Write day titles and narrative (write_narrative node) | Change `suggested_start_time` or route geometry |

**Structure from code. Orchestration from agent. Narrative from LLM.**
