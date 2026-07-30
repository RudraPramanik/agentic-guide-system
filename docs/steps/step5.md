# Wandr — P5 Cursor Prompts: Phase-Gated Tool Loop Agent
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P5 (7 days · 14 blueprint steps **5.1–5.14**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Layering (do not confuse):**
> - `docs/blueprint_final.md` = product / architecture source of truth
> - **this file** = Cursor build contract (sub-steps, failure boundaries, ✅ validation, tests)
> - OpenSpec = propose → apply → archive for **batched** implementation clusters (not one ceremony per micro-step)
>
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance until the current ✅ validation passes.
>
> Implement **from this prompt only**. Do not invent tools, phases, or HTTP SSE router behavior beyond what is locked here.

## Decision / Fix Log (read before implementing)

| # | Risk if unlocked | Lock in this prompt |
|---|---|---|
| 1 | `db` / `RoutingProvider` inside LangGraph `TravelState` → non-serializable checkpoints | `ToolContext` holds them; thread via closure / `RunnableConfig.configurable` |
| 2 | Blueprint 5.2 title “core six” vs 3 bullets → wrong tool split | **12-tool registry** is truth; 5.2 = DISCOVER(3); 5.3 = PLAN+VALIDATE+control+replan(9) |
| 3 | Reinvent `chat_with_tools` (already P0) | Step 5.4 = **verify + unit tests** only — do not reinstall litellm |
| 4 | Unbounded ReAct / invented tools | `TOOL_REGISTRY` names only; `PLANNER_MAX_TOOL_CALLS`; phase-filtered schemas |
| 5 | `finish_plan` without validate | Precondition: `validate_itinerary` ok **OR** `abort_triggered` |
| 6 | Narrative mutates stops/times | `write_narrative` outside loop; post-check place_ids ⊆ schedule; templates on LLM fail |
| 7 | Drop-retry then REPLAN over-thins | If day already has `dropped_stops` → prefer `expand_poi_search` over `drop_weakest_stop` |
| 8 | No-tool LLM stalls | Nudge → `tool_choice="required"` once → phase default tool; record in `tool_trace` |
| 9 | One DB session held 45s across LLM | Prefer per-tool session acquire; optional ctx.db only if measured need |
| 10 | P5 claims full HTTP SSE / trips save | Service event bridge + timeout only; **HTTP router + trips CRUD = P6** |
| 11 | Evaluation skipped on abort | `record_evaluation` always runs; `tool_trace` persisted |
| 12 | Magic phase / stuck rules inline | Transitions + stuck limit from settings / tables below — no invent |

---

## Prerequisites (P4 must be complete)

Before step 5.1, confirm P4 from `docs/context.md`:

- All P4 steps ✅ — travel_engine pure, CORS, `OsrmRoutingProvider`, `ToolResult` / `execute_tool` stub
- `python -m pytest tests/ -v` passes (141+ tests)
- `python scripts/test_p4_smoke.py` green
- Seeded + enriched + indexed destination available for smoke (Darjeeling default)
- **Already real (do NOT reinvent):**
  - `src/core/llm/client.py` — `chat_completion`, `chat_with_tools`, `LLMToolResponse`
  - `src/planner/routing_provider.py` — `OsrmRoutingProvider`
  - `src/travel_engine/*` — selector, allocator, optimizer, schedule, validator, protocols, rules
  - Planner settings in `get_settings()`: `PLANNER_MAX_TOOL_CALLS=12`, `PLANNER_MAX_REPLAN_ATTEMPTS=2`, `PLANNER_GENERATION_TIMEOUT_SECONDS=45`, `PLANNER_MIN_READINESS_SCORE=0.3`, `PLANNER_AGENT_PHASE_STUCK_LIMIT=3`
- Current stubs (do **NOT** assume APIs exist — files are ~1-line placeholders beyond the P4 envelope):
  - `src/planner/tools/*` bodies (registry empty except unknown→ok=False)
  - `src/planner/graph/*` (state, messages, nodes, builder)
  - `src/planner/service.py`, `src/planner/router.py`, `src/planner/schemas.py`
  - `src/evaluation/repository.py`, `service.py`, `schemas.py` (model exists)
- `langgraph` is **not** in `requirements.txt` yet — install at step 5.6

## Prompt conventions (every step)

- **Extend, don't replace** P0–P4 code unless the step explicitly says replace.
- **Tool rule:** nodes call `execute_tool(name, input, ctx)` only — never import tool impl functions in `planner/graph/nodes/`.
- **LLM rule:** only via `src/core/llm/client.py`. Never import litellm/groq/openai elsewhere.
- **Travel engine purity:** tools may call travel_engine; travel_engine still has **no** LLM/network/DB. Routing via `ctx.routing` only.
- **Geo / search:** Qdrant via `src/search/`; PostGIS radius via places repository; OSRM only through `OsrmRoutingProvider` → `geo/osrm`.
- **Env:** all via `get_settings()` — never `os.environ.get()`.
- **Time:** `datetime.now(timezone.utc)` for timestamps; schedule times remain naive `"HH:MM"` from travel_engine.
- **Windows:** use `Select-String` instead of `grep` where noted in validation.
- **No new packages** without `requirements.txt` + why-comment. Only expected new package in P5: `langgraph` (5.6).
- **Failure standards:** every code prompt has `─── FAILURE BOUNDARY ───` and a `✅ Failure path:` line.
- **OpenSpec cadence (implementation):** batch clusters — `5.1–5.3`, `5.4–5.5`, `5.6–5.8`, `5.9–5.11`, `5.12–5.14`. Do **not** run full propose→apply→archive for every single micro-step.

---

## P5 architecture (read before implementing)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         P5 dependency graph (canonical order)                │
└──────────────────────────────────────────────────────────────────────────────┘

  5.1 schemas + registry (12 tools registered; bodies may stub)
        │
  5.2 DISCOVER tools ──► 5.3 PLAN / VALIDATE / control / replan tools
        │
  5.4 verify chat_with_tools (already exists) + tests
        │
  5.5 phase gating + preconditions + maybe_transition_phase + tool_trace
        │
  5.6 TravelState (+ install langgraph)
        │
  5.7 messages.py (phase-aware prompt)
        │
  5.8 parse_preferences (fixed LLM bookend)
        │
  5.9 agent ↔ tool_executor loop nodes
        │
  5.10 write_narrative + record_evaluation (fixed bookends)
        │
  5.11 graph/builder.py compile
        │
  5.12 planner/service.py SSE event bridge + wait_for ceiling
        │
  5.13 pytest tool_loop ──► 5.14 scripts/test_agent.py + context.md

  Layer rules:
    tools/*              → typed I/O; soft-fail ToolResult; call travel_engine / search / readiness
    graph/nodes/*        → execute_tool + chat_* only; never tool impl imports
    ToolContext          → routing + optional db; NOT inside checkpointed TravelState
    travel_engine/*      → still pure (unchanged from P4)
    service SSE bridge   → emit events + timeout; HTTP StreamingResponse is P6
```

**Canonical build order (the only order stated in this document):**
```
5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 5.9 → 5.10 → 5.11 → 5.12 → 5.13 → 5.14
```

**Graph shape (locked):**
```
START → parse_preferences → agent ↔ tool_executor
  needs_clarification → END
  plan_complete → write_narrative → record_evaluation → END
  else → agent
```

---

## P5 design decisions (locked — no "optional" / either-or)

### AgentPhase + PHASE_TOOLS — LOCKED

```python
class AgentPhase(str, Enum):
    DISCOVER = "discover"
    PLAN = "plan"
    VALIDATE = "validate"
    REPLAN = "replan"
    WRAP_UP = "wrap_up"

PHASE_TOOLS = {
    AgentPhase.DISCOVER: ["check_readiness", "search_places", "rank_places", "ask_clarification"],
    AgentPhase.PLAN: ["build_route", "build_schedule"],
    AgentPhase.VALIDATE: ["validate_itinerary"],
    AgentPhase.REPLAN: ["reoptimize_routes", "drop_weakest_stop", "expand_poi_search", "accept_partial"],
    AgentPhase.WRAP_UP: ["finish_plan"],
}
```

### Phase transitions — LOCKED (deterministic; never LLM-chosen)

| From | Condition | To |
|------|-----------|-----|
| DISCOVER | `rank_places` succeeded | PLAN |
| PLAN | `build_schedule` succeeded | VALIDATE |
| VALIDATE | `validate_itinerary` ok=True | WRAP_UP |
| VALIDATE | errors AND `replan_loop_count < max` | REPLAN (increment `replan_loop_count` on entry) |
| VALIDATE | errors AND replan exhausted | WRAP_UP (`abort_triggered=True`) |
| REPLAN | any replan tool succeeded (except accept_partial) | PLAN |
| REPLAN | `accept_partial` OR replan max hit | WRAP_UP |
| Any | `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` | WRAP_UP (`abort_triggered=True`) |
| DISCOVER | `ask_clarification` succeeded | END via `needs_clarification=True` |

`maybe_transition_phase(state, tool_name, result)` is the only phase mutator besides agent ceiling / stuck paths.

### Default tool per phase (nudge / LLM fail) — LOCKED

| Phase | Default tool |
|-------|--------------|
| DISCOVER | `check_readiness` |
| PLAN | `build_route` |
| VALIDATE | `validate_itinerary` |
| REPLAN | `reoptimize_routes` |
| WRAP_UP | `finish_plan` |

### Stuck detector — LOCKED

Track a compact fingerprint of planning progress (e.g. phase + lens of candidates/ranked/route/schedule + last validation error codes). If fingerprint unchanged for `PLANNER_AGENT_PHASE_STUCK_LIMIT` consecutive tool-executor cycles:

- If phase ∈ {DISCOVER, PLAN, VALIDATE}: auto-advance to next phase in happy-path order (DISCOVER→PLAN→VALIDATE→WRAP_UP) and append warning `phase_stuck_auto_advance`.
- If phase == REPLAN: set `abort_triggered=True`, phase=WRAP_UP, warning `phase_stuck_replan_abort`.
- If phase == WRAP_UP: force `finish_plan` path / `plan_complete` attempt.

### ToolContext vs TravelState — LOCKED

- `TravelState`: serializable TypedDict / dict fields only (prefs, phase counters, working POI/route/schedule data, flags). **No** `db`, **no** `RoutingProvider`.
- `ToolContext`: `destination_id`, `base_lat`, `base_lng`, `routing`, optional `db`, helpers to read/write allowed state fields.
- Prefer acquire `AsyncSession` inside DB tools; do not hold one session for the full generation timeout.

### ToolResult envelope — LOCKED (extend P4)

```python
class ToolResult(BaseModel):
    ok: bool
    code: str | None = None      # e.g. precondition_failed, unknown_tool, llm_unavailable
    message: str | None = None
    data: dict | None = None
    fallback_used: bool = False
```

### finish_plan precondition — LOCKED

Succeed only if prior `validate_itinerary` returned ok **OR** `abort_triggered=True`. Else `ToolResult(ok=False, code="precondition_failed")`.

### Structure from code, narrative from LLM — LOCKED

LLM never invents place IDs, coordinates, stop order, or times. Those come from travel_engine + tools. Narrative = titles + paragraphs only.

### Evaluation — LOCKED

Always persist via `record_evaluation` (including abort / clarification after parse). Ranking rationales in `tool_trace` only — **no** new TripEvaluation column / migration. Model already has `tool_trace`, `tool_loop_count`, `agent_phase_reached`, resilience flags.

### SSE scope — LOCKED (P5 vs P6)

| In P5 (5.12) | Deferred to P6 |
|--------------|----------------|
| Service hooks emit `tool_started` / `tool_done` / `phase_changed` | `POST /api/v1/planner/generate` StreamingResponse |
| `asyncio.wait_for(..., PLANNER_GENERATION_TIMEOUT_SECONDS)` around graph invoke | Disconnect cancel + asyncio.Queue design |
| In-memory event list / callback for tests | Trips `save_from_state`, Redis cache |
| | `PLANNER_ABSOLUTE_MIN_PLACES` HTTP pre-graph floor |

### Design patterns (teaching + structure)

| Module | Pattern | Meaning |
|--------|---------|---------|
| `tools/registry` | Registry + Command | Named tools only; one execute entry point |
| `AgentPhase` / `PHASE_TOOLS` | State machine | Phase gating; LLM never chooses phase |
| `ToolContext` | Context Object / DI | Non-serializable deps outside checkpoints |
| `agent` ↔ `tool_executor` | Bounded ReAct | Ceiling + phase tools + validate-before-finish |
| `write_narrative` | Fixed bookend | Narrative only; geometry immutable |
| `OsrmRoutingProvider` | Adapter (P4) | Injected as `ctx.routing` |

### Forward locks (design-only — do not implement in P5)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | `POST /planner/generate` SSE StreamingResponse + disconnect cancel | P6.2 |
| F2 | `TripService.save_from_state` + guest ownership | P6.1 |
| F3 | `PLANNER_ABSOLUTE_MIN_PLACES` pre-graph HTTP reject | P6.2 |
| F4 | Redis planner cache | P6.4 |
| F5 | Edit/replan HTTP API | P7 |

---

## Step 5.1 — tools/schemas.py + registry.py (12 tools registered)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Expand P4 ToolResult envelope into full tool schemas + AgentPhase + ToolContext
shapes + register all 12 tools (fn may be stub returning not_implemented until 5.2/5.3).
This is step 5.1. No new packages.

─── IMPLEMENT / EXTEND src/planner/tools/schemas.py ───

  - AgentPhase enum (values above)
  - PHASE_TOOLS: dict[AgentPhase, list[str]] — exact mapping from Locked decisions above
  - ToolResult (extend with fallback_used if missing)
  - ToolTraceEntry: name, ok, ms, phase, code?, fallback_used?
  - PendingToolCall: name, arguments_json (str), id?: str
  - ToolContext: destination_id, base_lat, base_lng, routing (Protocol/Any),
    db optional, and a reference or callbacks to mutate allowed TravelState fields
    (may use a lightweight Protocol / plain object — do NOT put ctx inside LangGraph state)
  - Per-tool input models (minimal fields OK; expand in 5.2/5.3 as needed):
      CheckReadinessIn, SearchPlacesIn, RankPlacesIn, BuildRouteIn, BuildScheduleIn,
      ValidateItineraryIn, FinishPlanIn, AskClarificationIn, ReoptimizeRoutesIn,
      DropWeakestStopIn, ExpandPoiSearchIn, AcceptPartialIn
  - Empty input models may be `BaseModel` with no fields where the tool reads from state/ctx only

─── IMPLEMENT / EXTEND src/planner/tools/registry.py ───

  TOOL_REGISTRY: dict[str, ToolDefinition] where ToolDefinition has at least:
    fn, input_model, allowed_phases: list[AgentPhase], preconditions (callable or None)

  Register all 12 names from PHASE_TOOLS union.
  Stub fns may return ToolResult(ok=False, code="not_implemented") until 5.2/5.3.

  async def execute_tool(name, input, ctx) -> ToolResult:
    1. unknown → unknown_tool
    2. phase not allowed → precondition_failed (no fn call)
    3. precondition fail → precondition_failed
    4. try/except around fn → never raise; ok=False with code=tool_error
    5. (full tool_trace + tool_loop_count increment completed in 5.5 — here at minimum never raise)

  def get_tools_for_phase(phase: AgentPhase) -> list[dict]:
    """OpenAI function schemas from input_model.json_schema() — filtered by PHASE_TOOLS[phase]."""

─── RULES ───
- Extend P4 files; keep unknown_tool soft-fail behavior.
- Do not implement real tool bodies yet (5.2/5.3).
- Do not add langgraph yet.

─── FAILURE BOUNDARY ───
Wrong-phase / unknown / stub → ToolResult(ok=False). Must NOT: raise to caller.

─── VALIDATION ───
  python -c "
from src.planner.tools.schemas import AgentPhase, ToolResult, PHASE_TOOLS
from src.planner.tools.registry import execute_tool, get_tools_for_phase, TOOL_REGISTRY
import asyncio
from pydantic import BaseModel

# PHASE_TOOLS may live in schemas or registry — import from where you placed it
assert len(TOOL_REGISTRY) == 12
schemas = get_tools_for_phase(AgentPhase.DISCOVER)
names = {s['function']['name'] for s in schemas}
assert names == set(PHASE_TOOLS[AgentPhase.DISCOVER])

class Empty(BaseModel):
    pass

async def main():
    # Fake ctx with agent_phase DISCOVER — shape as implemented
    class Ctx:
        state = type('S', (), {'agent_phase': AgentPhase.DISCOVER, 'tool_loop_count': 0, 'tool_trace': []})()
    r = await execute_tool('build_route', Empty(), Ctx())  # wrong phase
    assert r.ok is False and r.code in ('precondition_failed', 'not_implemented', 'unknown_tool')
    print('PASS — 5.1 registry + phase filter surface')
asyncio.run(main())
"

✅ Failure path: execute_tool('nope', ...) → ok=False code=unknown_tool; never raise.
```

---

## Step 5.2 — DISCOVER tools (check_readiness, search_places, rank_places)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement the three DISCOVER tool bodies. This is step 5.2.
Note: Blueprint labels 5.2 “core six”; this prompt locks DISCOVER-only here (see Decision Log #2).

─── IMPLEMENT ───

  src/planner/tools/check_readiness.py
    - Load destination counts (place/enrich/index) via repository/service; call compute_readiness
      or DestinationService.get_readiness
    - Set state.readiness_score
    - If score < PLANNER_MIN_READINESS_SCORE → warning in data/message; still ok=True
      (does NOT block generation)
    - Acquire DB session inside tool if needed

  src/planner/tools/search_places.py
    - Prefer Qdrant search_places (destination-scoped) with query from interests/raw prefs
    - On empty / search unavailable → PostGIS radius fallback via PlaceRepository.find_within_radius
    - Set state.used_geo_fallback=True on fallback path
    - Map Place rows → PlaceCandidate-shaped dicts on state.candidate_pois
    - Soft-fail empty list ok=True with code/warning rather than raise

  src/planner/tools/rank_places.py
    - Map candidates → travel_engine PlaceCandidate + TripPreferences from state
    - select_places + explain_selection for top_n explanations into tool data / tool_trace later
    - Write state.ranked_pois
    - Pure ranking — no LLM

─── RULES ───
- Wire fns into TOOL_REGISTRY.
- No litellm imports. No direct httpx.
- Map ORM → engine types at tool boundary.

─── FAILURE BOUNDARY ───
Qdrant down → PostGIS fallback + used_geo_fallback. Must NOT: 500 / raise to graph.
Readiness low → warning only.

─── VALIDATION ───
  # Unit-style with mocked ctx / Fake repos — full cases in 5.13
  python -c "
from src.planner.tools import check_readiness, search_places, rank_places
from src.planner.tools.registry import TOOL_REGISTRY
for name in ('check_readiness','search_places','rank_places'):
    assert name in TOOL_REGISTRY
    assert TOOL_REGISTRY[name].fn is not None
print('PASS — 5.2 DISCOVER tools registered')
"

✅ Failure path: mocked Qdrant failure → search_places sets used_geo_fallback (assert in 5.13).
```

---

## Step 5.3 — PLAN / VALIDATE / control / replan tools

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement remaining nine tools. This is step 5.3.

─── IMPLEMENT ───

  build_route:
    - allocate_days(ranked, days) → per day optimize_route(..., ctx.routing, base_lat/lng)
    - Persist route + dropped_stops onto state; set used_osrm_fallback if any RouteLeg.used_fallback
    - FakeRoutingProvider OK in tests

  build_schedule:
    - For each day: build_day_schedule(ordered, consecutive legs)
    - Write state.schedule with suggested_start_time on every stop

  validate_itinerary:
    - Map schedule/route → TripItinerary; call validate_trip
    - ok=True iff ValidationResult.passed; data includes errors/warnings
    - Remember P4: empty itinerary → passed=False errors=["empty_itinerary"]

  finish_plan:
    - Precondition: last validate ok OR abort_triggered
    - Sets plan_complete=True

  ask_clarification:
    - Sets needs_clarification=True + clarification_question from input
    - ok=True; loop exits via graph conditional (5.11)

  reoptimize_routes:
    - Re-run route+schedule for all days with current ranked set

  drop_weakest_stop:
    - Remove lowest-scored stop on worst day; re-route that day
    - If that day already has dropped_stops from PLAN → still allowed but messages (5.7)
      tell the agent to prefer expand_poi_search

  expand_poi_search:
    - Increase search top_k × 1.5 (constant in tool or config — name it SEARCH_EXPAND_FACTOR=1.5)
    - Re-search → rank → route → schedule pipeline internally via tool fns / shared helpers
      (helpers OK; graph nodes still only use execute_tool)

  accept_partial:
    - abort_triggered=True; phase moves toward WRAP_UP via maybe_transition_phase

─── RULES ───
- Each tool: Pydantic I/O, allowed_phases, precondition function.
- finish_plan without validate → precondition_failed.
- Never raise; never call LLM inside these tools.

─── FAILURE BOUNDARY ───
Routing/search failures → ToolResult soft fail or degraded data + flags. Must NOT: uncaught exception.

─── VALIDATION ───
  python -c "
import asyncio
from uuid import uuid4
from src.planner.tools.registry import TOOL_REGISTRY, execute_tool
from src.planner.tools.schemas import AgentPhase
from pydantic import BaseModel

assert set(TOOL_REGISTRY) >= {
  'build_route','build_schedule','validate_itinerary','finish_plan','ask_clarification',
  'reoptimize_routes','drop_weakest_stop','expand_poi_search','accept_partial',
}

class Empty(BaseModel):
    pass

class Ctx:
    class S:
        agent_phase = AgentPhase.WRAP_UP
        abort_triggered = False
        validation_result = None
        tool_loop_count = 0
        tool_trace = []
        # minimal fields tools may touch
    state = S()
    destination_id = uuid4()
    base_lat = 27.04
    base_lng = 88.26
    routing = None
    db = None

async def main():
    r = await execute_tool('finish_plan', Empty(), Ctx())
    assert r.ok is False and r.code == 'precondition_failed'
    print('PASS — 5.3 finish_plan precondition')
asyncio.run(main())
"

✅ Failure path: finish_plan without validate → precondition_failed.
✅ Happy path (also 5.13): build_route + FakeRoutingProvider → ordered stops.
```

---

## Step 5.4 — Verify / harden chat_with_tools (already exists)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Do NOT rewrite from scratch. Verify P0 `chat_with_tools` matches blueprint contract and add tests.
This is step 5.4. No new packages.

─── VERIFY src/core/llm/client.py ───

  Already present:
    async def chat_with_tools(messages, tools, tool_choice="auto", model=None) -> LLMToolResponse
  Must:
    - Pass tools + tool_choice to litellm.acompletion
    - Parse tool_calls → [{name, arguments_json}]
    - Content-only → tool_calls=[] + content
    - Same tenacity contract as chat_completion (Timeout / RateLimitError)
    - Raise WandrLLMError after retries exhausted

─── CREATE / EXTEND tests/core/test_llm_chat_with_tools.py ───

  - Mock litellm.acompletion with a tool_call → parsed name + arguments_json
  - Mock content-only → empty tool_calls, content set
  - Optional: RateLimitError path retries (match existing chat_completion tests style)

─── RULES ───
- No second LLM gateway. No direct litellm imports outside client.py.

─── FAILURE BOUNDARY ───
Provider down → WandrLLMError after retries. Must NOT: hang without timeout.

─── VALIDATION ───
  python -m pytest tests/core/test_llm_chat_with_tools.py -v

✅ Failure path: mocked exhausted retries → WandrLLMError (assert in test).
```

---

## Step 5.5 — Phase gating + preconditions + transitions + tool_trace

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Complete registry orchestration: get_tools_for_phase, check_preconditions,
maybe_transition_phase, tool_trace append, tool_loop_count increment on every execute_tool.
This is step 5.5.

─── IMPLEMENT in registry.py (and small helpers module if needed) ───

  def check_preconditions(name, state) -> tuple[bool, str | None]: ...

  def maybe_transition_phase(state, tool_name, result) -> None:
      """Apply locked transition table. Increment replan_loop_count only on REPLAN entry."""

  def apply_tool_result(state, name, result) -> None:
      """Merge result.data into state fields per tool; append ToolTraceEntry; never raise."""

  execute_tool MUST:
    - reject wrong phase before fn
    - append tool_trace with ms timing
    - increment tool_loop_count exactly once per call (including failed preconditions? 
      LOCKED: increment on every execute_tool invocation after name resolves in registry,
      including precondition_failed; unknown_tool does NOT increment)

─── RULES ───
- LLM never sets agent_phase.
- Transitions only via maybe_transition_phase + agent ceiling/stuck.

─── FAILURE BOUNDARY ───
Wrong-phase → precondition_failed, no side effects on route/schedule.

─── VALIDATION ───
  python -c "
from src.planner.tools.schemas import AgentPhase
from src.planner.tools import registry
# Simulate: DISCOVER + rank_places ok → PLAN
state = registry._make_test_state() if hasattr(registry, '_make_test_state') else None
print('PASS — import transition helpers', registry.maybe_transition_phase, registry.get_tools_for_phase)
"

  # Prefer real asserts in tests/planner/test_phase_transitions.py (land with 5.13 if needed):
  # rank_places success → PLAN; validate fail with replan budget → REPLAN; max replan → WRAP_UP abort

✅ Failure path: wrong-phase tool rejected without executing fn (spy/mock fn call count == 0).
```

---

## Step 5.6 — TravelState + install langgraph

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Define TravelState and add langgraph dependency. This is step 5.6.
📦 langgraph — agent graph (append requirements.txt with why-comment)

─── UPDATE requirements.txt ───

  langgraph>=0.2.0  # P5.6 — phase-gated planner agent graph

  # pin a concrete tested version when installing; document in comment

─── IMPLEMENT src/planner/graph/state.py ───

  TravelState as TypedDict (total=False where needed) with fields from blueprint:

  Input: destination_id, destination_name, destination_lat, destination_lng,
         raw_input, session_id, base_lat, base_lng
  Prefs: days, budget, interests, include_offbeat, include_trekking
  Loop: agent_phase, tool_loop_count, pending_tool_calls, tool_trace,
        plan_complete, needs_clarification, clarification_question
  Resilience: replan_loop_count, max_replan_attempts, abort_triggered,
              llm_retry_count, used_geo_fallback, used_osrm_fallback, readiness_score
  Working: candidate_pois, ranked_pois, route, schedule, itinerary, validation_result
  Output: errors, warnings, trace_id

  FORBIDDEN on TravelState: db, routing, ToolContext, AsyncSession, httpx clients

─── RULES ───
- Prefer JSON-serializable values (UUID as str OK if consistent).
- max_replan_attempts default from get_settings().PLANNER_MAX_REPLAN_ATTEMPTS at invoke time.

─── FAILURE BOUNDARY ───
Must NOT: embed non-serializable resources in state.

─── VALIDATION ───
  python -c "
from src.planner.graph.state import TravelState
import typing
hints = typing.get_type_hints(TravelState)
assert 'db' not in hints and 'routing' not in hints
print('PASS — TravelState fields', len(hints))
"

  python -c "import langgraph; print('PASS — langgraph', langgraph.__version__ if hasattr(langgraph,'__version__') else 'import ok')"

✅ Failure path: N/A for types — import/install failure blocks progress.
```

---

## Step 5.7 — messages.py — agent prompt

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Build compact agent messages for chat_with_tools. This is step 5.7.

─── IMPLEMENT src/planner/graph/messages.py ───

  def build_agent_messages(state: TravelState) -> list[dict]:
    """
    System prompt MUST include:
      - Role: trip planner tool-using agent
      - Current phase + allowed tool names only
      - Hard rules: never invent places/IDs/coords/times/order; call tools to act
      - Compact state summary: days, interests, candidate/ranked counts,
        last validation errors, whether any day has dropped_stops
      - REPLAN guidance: if dropped_stops present → prefer expand_poi_search
        over drop_weakest_stop
      - Last 5 tool_trace entries only (token control) — NOT full history
    """

─── RULES ───
- No tool schemas inlined as free text inventable tools — schemas come from get_tools_for_phase.
- Keep message payload compact.

─── FAILURE BOUNDARY ───
Missing optional state fields → safe defaults in summary; must not raise.

─── VALIDATION ───
  python -c "
from src.planner.graph.messages import build_agent_messages
from src.planner.tools.schemas import AgentPhase
state = {
  'agent_phase': AgentPhase.REPLAN,
  'days': 3,
  'interests': ['photography'],
  'tool_trace': [],
  'route': [{'dropped_stops': [{'reason': 'exceeded_max_daily_travel'}]}],
  'errors': [],
  'warnings': [],
}
msgs = build_agent_messages(state)
assert any(m['role']=='system' for m in msgs)
text = msgs[0]['content'].lower()
assert 'expand_poi_search' in text
print('PASS — 5.7 messages')
"

✅ Failure path: empty tool_trace → still returns valid messages list.
```

---

## Step 5.8 — nodes/parse_preferences.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Fixed LLM bookend before the tool loop. This is step 5.8.

─── IMPLEMENT src/planner/graph/nodes/parse_preferences.py ───

  async def parse_preferences(state) -> dict:
    - chat_completion(..., response_format JSON) parsing
      {days, budget, interests, include_offbeat, include_trekking}
    - On WandrLLMError OR bad JSON:
        defaults: days=3, budget="mid", interests=[], include_offbeat=False,
        include_trekking=False
        increment llm_retry_count
    - Never blocks the graph

─── RULES ───
- NOT part of tool loop. Uses chat_completion — not chat_with_tools.
- Map interest strings toward PLACE_TAG_VOCAB when obvious; unknown interests kept but
  scoring may yield 0 (engine-safe).

─── FAILURE BOUNDARY ───
LLM down → defaults. Must NOT: abort generation solely because parse failed.

─── VALIDATION ───
  python -c "
import asyncio
from unittest.mock import AsyncMock, patch
from src.core.exceptions import WandrLLMError

async def main():
    with patch('src.planner.graph.nodes.parse_preferences.chat_completion',
               new=AsyncMock(side_effect=WandrLLMError(code='llm_unavailable', message='down'))):
        from src.planner.graph.nodes.parse_preferences import parse_preferences
        out = await parse_preferences({'raw_input': '3 days offbeat photography', 'llm_retry_count': 0})
        assert out.get('days') == 3
        assert out.get('llm_retry_count', 1) >= 1
    print('PASS — 5.8 defaults on LLM fail')
asyncio.run(main())
"

  # Happy path (mocked JSON): "3 days offbeat photography" → days=3, interests include photography/offbeat

✅ Failure path: kill LLM → defaults applied (above).
```

---

## Step 5.9 — nodes/agent.py + tool_executor.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Bounded agent ↔ tool_executor loop nodes. This is step 5.9.

─── IMPLEMENT src/planner/graph/nodes/agent.py ───

  async def agent_node(state, config=None) -> dict:
    1. If tool_loop_count >= PLANNER_MAX_TOOL_CALLS → abort_triggered, WRAP_UP; return
    2. tools = get_tools_for_phase(state.agent_phase)
    3. response = await chat_with_tools(build_agent_messages(state), tools, tool_choice="auto")
    4. If tool_calls → pending_tool_calls
    5. Else LOCKED nudge path:
         append system nudge; retry tool_choice="required" once
         still none → execute default tool for phase via execute_tool (bypass LLM);
         record tool_trace nudge/default; append warning agent_no_tool_call
    6. On WandrLLMError → default tool once; llm_retry_count += 1

  Obtain ToolContext from config["configurable"]["tool_context"] (or closure factory).

─── IMPLEMENT src/planner/graph/nodes/tool_executor.py ───

  async def tool_executor_node(state, config=None) -> dict:
    for call in pending_tool_calls:
      parse args with tool input_model
      result = await execute_tool(name, input_model, ctx)
      apply_tool_result(...)
      maybe_transition_phase(...)
    clear pending_tool_calls
    run stuck detector (Decision: stuck fingerprint)

─── RULES ───
- Nodes never import tool implementation modules — only registry.execute_tool.
- DB tools acquire their own sessions.

─── FAILURE BOUNDARY ───
Tool errors → state warnings/errors via ToolResult; node must not raise.
LLM errors → default tool fallback.

─── VALIDATION ───
  # Integration deferred to 5.13; minimum:
  python -c "
from src.planner.graph.nodes import agent, tool_executor
print('PASS — 5.9 imports', agent.agent_node, tool_executor.tool_executor_node)
"

  Get-ChildItem -Path src/planner/graph/nodes -Recurse -Filter *.py |
    Select-String "from src\.planner\.tools\.(check_readiness|search_places|rank_places|build_route)"
  # Expected: zero matches (only registry / schemas imports)

✅ Failure path: max tool calls → abort_triggered (unit in 5.13).
```

---

## Step 5.10 — write_narrative.py + record_evaluation.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Fixed bookends after the loop. This is step 5.10.

─── IMPLEMENT src/planner/graph/nodes/write_narrative.py ───

  - Input: locked schedule + route structure (IDs/times already set)
  - chat_completion for day titles + paragraph per day ONLY
  - Post-check: any place_id mentioned by LLM must exist in schedule — strip/ignore extras
  - On WandrLLMError → template strings per day; llm_retry_count += 1
  - Writes state.itinerary combining structure + narrative
  - MUST NOT modify stop order, times, coords

─── IMPLEMENT src/planner/graph/nodes/record_evaluation.py + evaluation service ───

  - Implement src/evaluation/repository.py + service.record_generation(...) as needed
  - Persist: tool_trace, tool_loop_count, agent_phase_reached, readiness_score,
    used_geo_fallback, used_osrm_fallback, abort_triggered, validation_*, prefs, timings
  - ALWAYS runs (abort / clarification / success)
  - Prefer short-lived DB session inside this node/service
  - No new TripEvaluation columns

─── RULES ───
- evaluation never skipped.
- explain_selection strings already in tool_trace from rank_places — do not migrate schema.

─── FAILURE BOUNDARY ───
Narrative LLM fail → templates. Evaluation DB fail → log + set warning; LOCKED preference:
  still attempt best-effort write; if write fails, surface warning but do not crash SSE mid-flight
  without logging (tests may mock repo).

─── VALIDATION ───
  python -c "
from src.planner.graph.nodes.write_narrative import write_narrative
from src.planner.graph.nodes.record_evaluation import record_evaluation
print('PASS — 5.10 imports')
"

✅ Failure path: abort_triggered=True still invokes record_evaluation (assert in 5.13).
```

---

## Step 5.11 — graph/builder.py — compile graph

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Wire LangGraph and compile at import/startup. This is step 5.11.

─── IMPLEMENT src/planner/graph/builder.py ───

  build_planner_graph() / get_compiled_graph():
    parse_preferences → agent
    agent → tool_executor (when pending tools or default executed path needs executor —
      LOCKED structure: agent always edges to tool_executor if pending_tool_calls non-empty
      OR after default tool already applied inside agent — prefer: agent sets pending OR
      applies default via execute_tool then continues; simplest locked shape from blueprint:
        agent → tool_executor → conditional
    tool_executor → conditional:
      needs_clarification → END
      plan_complete → write_narrative → record_evaluation → END
      else → agent

  Compile once; cache singleton. Compilation error must surface at startup/import.

─── RULES ───
- Inject ToolContext via configurable when invoking.
- No orphan nodes.

─── FAILURE BOUNDARY ───
Compile failure → loud import/startup error before first request. Must NOT: silently skip nodes.

─── VALIDATION ───
  python -c "
from src.planner.graph.builder import build_planner_graph
g = build_planner_graph()
print('PASS — graph compiled', type(g))
"

✅ Failure path: N/A — broken wiring fails compile (fix before merge).
```

---

## Step 5.12 — planner/service.py — SSE event bridge (not HTTP router)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Service-level generation runner with event callbacks + timeout. This is step 5.12.
Do NOT implement POST /planner/generate StreamingResponse (P6).

─── IMPLEMENT src/planner/service.py ───

  class PlannerService:
    async def generate(self, *, destination_id, raw_input, base_lat, base_lng, session_id,
                       on_event: Callable[[str, dict], None] | None = None) -> TravelState:
      """
      1. Build initial TravelState + ToolContext(routing=OsrmRoutingProvider(), ...)
      2. Hook tool/phase emissions:
           on_event("tool_started", {...})
           on_event("tool_done", {...})
           on_event("phase_changed", {...})
         (wire via ctx callbacks or registry hooks — keep nodes free of FastAPI)
      3. await asyncio.wait_for(graph.ainvoke(...), timeout=PLANNER_GENERATION_TIMEOUT_SECONDS)
      4. On TimeoutError → mark abort/error on state; emit error event if on_event set; re-raise
         or return state with errors — LOCKED: return state with errors=["generation_timeout"]
         and abort_triggered=True after best-effort record_evaluation if not already run
      """

─── RULES ───
- No FastAPI router registration in this step.
- Timeout from get_settings().
- Guests/users persistence is P6.

─── FAILURE BOUNDARY ───
Timeout → controlled error on state, not hang. Must NOT: await graph without ceiling.

─── VALIDATION ───
  python -c "
import inspect
from src.planner.service import PlannerService
assert hasattr(PlannerService, 'generate')
src = inspect.getsource(PlannerService.generate)
assert 'wait_for' in src
print('PASS — 5.12 service bridge uses wait_for')
"

✅ Failure path: monkeypatch graph to sleep > timeout → errors include generation_timeout (test in 5.13).
```

---

## Step 5.13 — tests/planner/test_tool_loop.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Integration coverage for the tool loop. This is step 5.13.

─── CREATE tests/planner/test_tool_loop.py ───

  Use mocked chat_with_tools / chat_completion and FakeRoutingProvider.
  Seed minimal destination/places in db_session when search needs DB — or fully mock tools
  for pure phase-machine tests.

  Required cases:
  ★ Happy path: phase DISCOVER→…→WRAP_UP; plan_complete=True; tool_loop_count ≤ 8;
    every scheduled stop has suggested_start_time
  ★ Validation fail → REPLAN tools invoked; replan_loop_count ≤ PLANNER_MAX_REPLAN_ATTEMPTS
  ★ Max tool calls → abort_triggered=True; evaluation recorded
  ★ ask_clarification → needs_clarification=True; loop exits without plan_complete
  ★ finish_plan blocked without validate
  ★ wrong-phase tool → precondition_failed; fn not called
  ★ agent no-tool → nudge/default path recorded in tool_trace

─── ALSO ───
  tests/planner/test_phase_transitions.py (if not already)
  tests/core/test_llm_chat_with_tools.py (from 5.4)
  Import guards in tests or as assertions in this module

─── VALIDATION ───
  python -m pytest tests/planner tests/core/test_llm_chat_with_tools.py -v
  python -m pytest tests/ -v

✅ Failure path: failing tests block 5.14 — do not update context.md as P5 complete.
```

---

## Step 5.14 — scripts/test_agent.py + context.md

```
Read AGENT.md and docs/context.md before proceeding.

TASK: End-to-end smoke for the agent graph + update context after green. This is step 5.14.

─── CREATE scripts/test_agent.py ───

  """
  P5 smoke — run: python scripts/test_agent.py
  Prefer: PlannerService.generate(...) direct invoke (no HTTP router required).
  Input: raw_input="3 days offbeat photography budget"
  Destination: Darjeeling (resolve via DB search; require seeded+enriched+indexed)

  Sections (print headers; exit 1 on first failure — never ambiguous PASS):
    1) settings planner bounds present
    2) graph compiles
    3) generate() completes
    4) errors==[] (or only soft warnings), abort_triggered==False
    5) days==3; all stops have lat/lng + suggested_start_time
    6) tool_trace non-empty; print summary table
    7) evaluation row written (query DB)
    8) import guards: no litellm outside core/llm/client.py;
       no tool impl imports under graph/nodes;
       travel_engine still pure
    9) OPTIONAL: print Langfuse trace URL if keys configured
  """

─── UPDATE docs/context.md (ONLY after smoke + full pytest pass) ───

  - Last updated / Next step → P6.1
  - Progress rows 5.1–5.14 ✅
  - Implemented modules: planner tools, graph, service bridge, evaluation service
  - Stubs list: remove planner tool/graph stubs; keep trips CRUD / planner HTTP router as P6 stubs
  - Do NOT claim P6 complete
  - Do NOT register /planner/generate as live endpoint until P6

─── FAILURE BOUNDARY ───
Missing LLM keys / unseeded destination → fail loud with section header (document required env).
Must NOT: print ALL PASSED if any section failed.

─── VALIDATION ───
  python scripts/test_agent.py
  python -m pytest tests/ -v

  Get-ChildItem -Path src -Recurse -Filter *.py |
    Select-String "import litellm|from litellm" |
    Where-Object { $_.Path -notmatch "core\\llm\\client\.py" }
  # Expected: zero matches

  Get-ChildItem -Path src\travel_engine -Recurse -Filter *.py |
    Select-String "src\.geo|import httpx|litellm|qdrant"
  # Expected: zero matches

✅ Failure path: smoke exits non-zero with clear section header.
```

---

## P5 Complete — Full Verification Checklist

Before claiming P5 done in `docs/context.md`:

```bash
# ── Unit / integration ──
python -m pytest tests/ -v

# ── Smoke (needs LLM keys + seeded Darjeeling) ──
python scripts/test_agent.py

# ── Import guards (PowerShell) ──
Get-ChildItem -Path src -Recurse -Filter *.py |
  Select-String "import litellm|from litellm" |
  Where-Object { $_.Path -notmatch "core\\llm\\client\.py" }
# Expected: zero matches

Get-ChildItem -Path src\planner\graph\nodes -Recurse -Filter *.py |
  Select-String "from src\.planner\.tools\.(check_readiness|search_places|rank_places|build_route|build_schedule)"
# Expected: zero matches — nodes use execute_tool only

Get-ChildItem -Path src\travel_engine -Recurse -Filter *.py |
  Select-String "src\.geo|import httpx|litellm|qdrant"
# Expected: zero matches

# langgraph present
python -c "import langgraph; print('langgraph ok')"

# No HTTP generate claimed yet
python -c "from src.main import create_app; app=create_app(); paths=[getattr(r,'path',None) for r in app.routes]; assert not any(p and 'planner/generate' in p for p in paths); print('P6 router not registered yet — ok')"

echo "P5 COMPLETE — proceed to P6"
```

### P5 ship criteria

| Check | Expected |
|-------|----------|
| 12 tools registered | All names in TOOL_REGISTRY |
| Phase gating | Wrong-phase → precondition_failed; schemas filtered |
| Transitions | Deterministic table; LLM never sets phase |
| ToolContext | db/routing not on TravelState |
| Bounded loop | tool_loop_count ceiling → abort + WRAP_UP |
| No-tool nudge | required retry → default tool; traced |
| finish_plan | Blocked until validate ok or abort |
| Narrative | No geometry mutation; templates on LLM fail |
| Evaluation | Always written; tool_trace persisted |
| Graph | Compiles; bookends outside loop |
| Service bridge | wait_for ceiling; events callback |
| HTTP generate | **Not** registered (P6) |
| Import guards | litellm / tool-impl / travel_engine purity |
| pytest + smoke | Green; smoke fails loud by section |

### Recommended OpenSpec implementation batches

After this prompt is archived, implement with batched changes (example):

1. `5.1–5.3` — schemas/registry + all 12 tool bodies  
2. `5.4–5.5` — chat_with_tools verify + phase gating / transitions / tool_trace  
3. `5.6–5.8` — TravelState + langgraph + messages + parse_preferences  
4. `5.9–5.11` — agent loop nodes + narrative/eval + graph compile  
5. `5.12–5.14` — service SSE bridge + pytest + smoke + context.md  

Do **not** open a full propose→archive cycle for each single micro-step unless a design conflict appears.
