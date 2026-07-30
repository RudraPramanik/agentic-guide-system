# Wandr — P5 Patch Addendum
> **Status: APPLIED into `docs/steps/step5.md`** (and aligned in `docs/blueprint_final.md` + `AGENT.md`) via OpenSpec change `patch-step5-critic-runtime-fixes`. Do **not** re-apply these rewrites — treat this file as rationale / history only.
>
> Companion to the drafted `P5 Cursor Prompts` document. That draft correctly incorporated the
> P4 addendum's forward-locks (ToolContext/TravelState separation, session-per-tool, SSE scope
> split, REPLAN prioritizing `expand_poi_search` over `drop_weakest_stop`). This patch covers
> what a close read against actual LangGraph execution semantics surfaced — issues that pass a
> single-tool-call unit test cleanly and then break silently under real, concurrent, multi-turn
> use. Apply these before implementing steps 5.9 and 5.11 — those two steps depend most directly
> on the fixes below.

## Fix Log

| # | Issue | Fix |
|---|---|---|
| 1 | `ToolContext` threading left as "`config` or closure factory" — a closure over a shared, cached compiled graph would leak context between concurrent requests | Lock to `config["configurable"]["tool_context"]` only; closures/module-globals explicitly forbidden |
| 2 | Two possible tool-execution pathways (`agent_node` sometimes calls `execute_tool` directly in the fallback case; `tool_executor_node` normally does) — bookkeeping drift, graph-edge ambiguity | `agent_node` never executes tools — it only ever sets `pending_tool_calls` (real or synthesized-default); `tool_executor_node` is unconditionally the sole caller of `execute_tool`; graph edge is unconditionally `agent → tool_executor` |
| 3 | No rule on how list-shaped state fields (`tool_trace`, `warnings`, `errors`) accumulate across node returns — LangGraph's default merge behavior for a plain field is last-write-wins, which would silently drop trace history | Nodes always read-append-return the full list in Python; never rely on `Annotated`/reducer merge semantics for this |
| 4 | Timeout path in `PlannerService.generate` likely can't access the `TravelState` accumulated inside the now-cancelled graph task, so the "best-effort evaluation write" has nothing real to write | Track a service-level `last_known_state` reference, updated by the same hooks that emit SSE events, independent of the cancellable task |
| 5 | Two mutation pathways into `TravelState` — tools described as having "callbacks to mutate allowed fields" AND `apply_tool_result` merging `ToolResult.data` | Tools only ever read a read-only state view and return `ToolResult`; `apply_tool_result` is the sole writer |
| 6 | `unknown_tool` doesn't increment `tool_loop_count`; the stuck-detector is the only real backstop against infinite hallucinated-tool-name loops, but this dependency is never stated | State explicitly: stuck-detector MUST run unconditionally every `tool_executor_node` cycle, regardless of whether a real tool executed |
| 7 | `langgraph>=0.2.0` — floating pin, inconsistent with every other phase's exact-pin convention | Pin an exact tested version, e.g. `langgraph==0.2.x` |
| 8 | REPLAN tools' internal multi-step chaining under one `execute_tool` call is asymmetric vs. DISCOVER/PLAN's one-action-per-call pattern, with no stated rationale | Document as an intentional, deliberate coarse-graining for recovery actions |

---

## Fix 1 — `ToolContext` threading: `config` only, never a closure

**Why this matters:** step 5.11 caches one compiled graph instance and reuses it across every
call to `PlannerService.generate()`. If any node obtains its `ToolContext` via a closure bound
at graph-construction time (or any module-level/global reference), every concurrent request
sharing that one compiled graph would see whichever `ctx` was set most recently — mixing up
`destination_id`, `routing`, and `db` between unrelated users' generations. This is a real
cross-request data-leak risk, not a hypothetical one, given "compile once; cache singleton" is
explicitly the locked design in 5.11.

### Rewrite for step 5.9 / 5.12

```python
# planner/service.py — every invocation passes a FRESH ToolContext via config
async def generate(self, *, destination_id, raw_input, base_lat, base_lng, session_id, on_event=None):
    ctx = ToolContext(
        destination_id=destination_id, base_lat=base_lat, base_lng=base_lng,
        routing=OsrmRoutingProvider(), db=None,  # DB acquired per-tool, not held here
    )
    graph = get_compiled_graph()  # cached singleton — shared across ALL concurrent calls
    config = {"configurable": {"tool_context": ctx}}
    state = build_initial_state(destination_id, raw_input, base_lat, base_lng, session_id)
    result = await asyncio.wait_for(graph.ainvoke(state, config=config), timeout=...)
```

```python
# planner/graph/nodes/agent.py and tool_executor.py — retrieve ctx from config, every call
async def agent_node(state, config) -> dict:
    ctx: ToolContext = config["configurable"]["tool_context"]
    ...

async def tool_executor_node(state, config) -> dict:
    ctx: ToolContext = config["configurable"]["tool_context"]
    ...
```

**LOCKED rule:** no node function may reference `ctx` via a closure, module-level variable, or
any mechanism other than `config["configurable"]["tool_context"]`. Add this to `AGENT.md`'s
planner-specific rules alongside "agent tool calls MUST use names from `TOOL_REGISTRY` only."

### New test for step 5.13

```python
async def test_concurrent_generations_do_not_leak_context():
    """
    Two concurrent generate() calls with DIFFERENT destination_ids against the SAME cached
    compiled graph must each see their own ToolContext throughout — direct regression test
    for the closure-vs-config concurrency risk.
    """
    graph = get_compiled_graph()
    ctx_a = ToolContext(destination_id=uuid4(), base_lat=1.0, base_lng=1.0, routing=Fake(), db=None)
    ctx_b = ToolContext(destination_id=uuid4(), base_lat=2.0, base_lng=2.0, routing=Fake(), db=None)
    # invoke both concurrently (asyncio.gather), assert each node saw its OWN ctx.destination_id
    # (instrument a spy tool or check tool_trace data for the destination_id used)
```

---

## Fix 2 — Unify tool execution into a single pathway

**Why this matters:** as drafted, `agent_node` sometimes calls `execute_tool` directly (the
no-tool-call fallback path), and sometimes just sets `pending_tool_calls` for
`tool_executor_node` to process normally. Two execution pathways means `tool_trace`/
`tool_loop_count` bookkeeping can differ depending on which path fired, and the graph's edge
logic has to special-case which one happened — which is visibly why step 5.11's own pseudocode
struggles to state a single, clean edge rule.

### Rewrite for step 5.9

```python
async def agent_node(state, config) -> dict:
    """
    ONLY decides what tool(s) to attempt next. NEVER calls execute_tool itself.
    """
    if state["tool_loop_count"] >= settings.PLANNER_MAX_TOOL_CALLS:
        return {"abort_triggered": True, "agent_phase": AgentPhase.WRAP_UP, "pending_tool_calls": []}

    tools = get_tools_for_phase(state["agent_phase"])
    response = await chat_with_tools(build_agent_messages(state), tools, tool_choice="auto")

    if response.tool_calls:
        return {"pending_tool_calls": response.tool_calls}

    # No tool call — nudge once with tool_choice="required"
    nudged = await chat_with_tools(
        build_agent_messages(state, nudge=True), tools, tool_choice="required",
    )
    if nudged.tool_calls:
        return {"pending_tool_calls": nudged.tool_calls, "warnings": state["warnings"] + ["agent_nudged"]}

    # Still nothing — SYNTHESIZE the phase default as a pending call. Do NOT execute it here.
    default_name = DEFAULT_TOOL_BY_PHASE[state["agent_phase"]]
    synthesized = [PendingToolCall(name=default_name, arguments_json="{}")]
    return {
        "pending_tool_calls": synthesized,
        "warnings": state["warnings"] + ["agent_no_tool_call_default_used"],
    }
```

```python
async def tool_executor_node(state, config) -> dict:
    """
    The ONLY place execute_tool is ever called — for both real LLM tool calls and
    synthesized defaults. Unconditional every cycle.
    """
    ctx = config["configurable"]["tool_context"]
    new_trace = list(state["tool_trace"])   # Fix 3: read full list, append, return whole
    working_state = dict(state)

    for call in state["pending_tool_calls"]:
        input_model = parse_tool_input(call.name, call.arguments_json)
        result = await execute_tool(call.name, input_model, ctx, working_state)
        working_state = apply_tool_result(working_state, call.name, result)   # Fix 5: sole writer
        new_trace.append(ToolTraceEntry(name=call.name, ok=result.ok, ...))
        maybe_transition_phase(working_state, call.name, result)

    working_state["pending_tool_calls"] = []
    working_state["tool_trace"] = new_trace
    run_stuck_detector(working_state)   # Fix 6: unconditional, every cycle
    return working_state
```

### Rewrite for step 5.11's graph edges

```
parse_preferences → agent
agent → tool_executor                         # UNCONDITIONAL, every time
tool_executor → conditional:
    needs_clarification → END
    plan_complete       → write_narrative → record_evaluation → END
    else                 → agent
```
No special-casing based on "did agent already execute something" — it never does.

### New test for step 5.13

```python
async def test_no_tool_call_synthesizes_default_and_goes_through_executor():
    """
    Mock chat_with_tools to return no tool_calls even after the required-retry nudge.
    Assert: pending_tool_calls contains the phase's default tool, tool_executor_node is what
    actually calls execute_tool (spy on registry.execute_tool call count == 1), and
    tool_trace records the default-tool execution with warning agent_no_tool_call_default_used.
    """
```

---

## Fix 3 — List-state accumulation is explicit Python, not a LangGraph reducer

**LOCKED rule for step 5.6 / 5.9:** every node function that touches a list-shaped
`TravelState` field (`tool_trace`, `warnings`, `errors`) reads the CURRENT full list, appends
in plain Python, and returns the complete extended list. No node relies on `Annotated[list, ...]`
merge semantics to accumulate entries — state fields are treated as last-write-wins, and the
"last write" is always the full, already-extended value.

```python
# WRONG — assumes LangGraph additively merges this list
return {"tool_trace": [new_entry]}

# RIGHT — always return the complete list
return {"tool_trace": state["tool_trace"] + [new_entry]}
```

### New test for step 5.13

```python
async def test_tool_trace_accumulates_across_multiple_cycles():
    """
    Run a scripted sequence of >=4 tool_executor_node cycles (mocked tools). Assert
    len(final_state['tool_trace']) == 4, not 1 — direct regression test for the
    replace-vs-accumulate LangGraph state-merge risk. A naive implementation that returns
    only the newest entry each cycle would fail this test immediately and obviously.
    """
```

---

## Fix 4 — Timeout path needs state tracked outside the cancellable task

**Why this matters:** `asyncio.wait_for` cancels the graph task on timeout; whatever
`TravelState` existed inside that task at the moment of cancellation is not reliably
accessible to the caller afterward unless it was being captured somewhere else the whole time.
As drafted, `record_evaluation`'s "best-effort write" after a timeout would have nothing real
to write.

### Rewrite for step 5.12

```python
class PlannerService:
    async def generate(self, *, destination_id, raw_input, base_lat, base_lng, session_id, on_event=None):
        last_known_state: dict = {}   # updated by hooks below, lives OUTSIDE the cancellable task

        def _capture_and_emit(event: str, data: dict, state_snapshot: dict | None = None):
            if state_snapshot is not None:
                last_known_state.clear()
                last_known_state.update(state_snapshot)   # cheap dict copy each hook fire
            if on_event:
                on_event(event, data)

        ctx = ToolContext(destination_id=destination_id, base_lat=base_lat, base_lng=base_lng,
                           routing=OsrmRoutingProvider(), db=None)
        config = {"configurable": {"tool_context": ctx, "emit": _capture_and_emit}}
        initial_state = build_initial_state(destination_id, raw_input, base_lat, base_lng, session_id)

        try:
            final_state = await asyncio.wait_for(
                graph.ainvoke(initial_state, config=config),
                timeout=settings.PLANNER_GENERATION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            final_state = {
                **last_known_state,   # whatever progress was captured before cancellation
                "errors": last_known_state.get("errors", []) + ["generation_timeout"],
                "abort_triggered": True,
            }
            _capture_and_emit("error", {"code": "generation_timeout"})

        await record_evaluation(final_state)   # ALWAYS runs, now with real accumulated data
        return final_state
```

Nodes call `config["configurable"]["emit"](event, data, state_snapshot=working_state)` at each
meaningful checkpoint (after `tool_executor_node` applies a result, at minimum) so
`last_known_state` reflects real progress, not just UI event payloads.

### New test for step 5.13

```python
async def test_timeout_produces_nonempty_evaluation():
    """
    Monkeypatch the graph to sleep past PLANNER_GENERATION_TIMEOUT_SECONDS after at least
    one tool_executor cycle has run and emitted. Assert the resulting evaluation record has
    a non-empty tool_trace (not just errors=['generation_timeout'] with nothing else) —
    proves last_known_state actually captured pre-timeout progress.
    """
```

---

## Fix 5 — Tools never mutate state directly

**LOCKED rule for step 5.1:** `ToolContext` exposes a read-only snapshot of whatever state a
tool needs to read (destination/prefs/candidates/etc.) — it does NOT expose any callback or
reference that lets a tool function write back into `TravelState`. The only place state is
ever mutated is `apply_tool_result(working_state, tool_name, result)` inside
`tool_executor_node` (Fix 2's rewrite). This makes every tool a pure function of
`(input, ctx-read-only) → ToolResult`, trivially unit-testable in isolation, and gives exactly
one auditable place where state changes — critical for debugging an agent loop where things
can go wrong many steps into a run.

Remove the "reference or callbacks to mutate allowed TravelState fields" language from step
5.1's `ToolContext` description entirely.

---

## Fix 6 — State explicitly why `unknown_tool` not incrementing the ceiling is safe

**Add to step 5.5's rationale, verbatim:**

> `unknown_tool` deliberately does not increment `tool_loop_count` — a hallucinated tool name
> is not "an attempted real step" the way a wrong-phase-but-real tool name is. This is safe
> ONLY because the stuck-detector (step 5.9, `tool_executor_node`) runs unconditionally on
> EVERY cycle, regardless of whether the resolved tool was unknown, precondition-failed, or
> successfully executed. If the stuck-detector is ever changed to only run after a real tool
> executes, this reopens a hole: an LLM that persistently hallucinates nonexistent tool names
> would loop until the blunt `PLANNER_GENERATION_TIMEOUT_SECONDS` wall-clock timeout instead of
> the intended graceful `PLANNER_AGENT_PHASE_STUCK_LIMIT`-based abort. Do not make the
> stuck-detector conditional on tool validity.

### New test for step 5.13

```python
async def test_persistent_unknown_tool_hits_stuck_detector_not_timeout():
    """
    Mock chat_with_tools to always return a tool_call naming a nonexistent tool, every cycle.
    Assert the run terminates via abort_triggered from the stuck-detector within
    PLANNER_AGENT_PHASE_STUCK_LIMIT cycles — NOT by exhausting tool_loop_count (which never
    increments for unknown_tool) and NOT by hitting the wall-clock timeout.
    """
```

---

## Fix 7 — pin `langgraph` exactly

```
langgraph==0.2.XX  # P5.6 — phase-gated planner agent graph; pin exact per project convention
                    # (matches qdrant-client==1.15.1, sentence-transformers==5.1.2 style pins)
```
Replace the exact `XX` with whatever version is actually installed and verified working during
step 5.6 — never leave a floating `>=` in `requirements.txt`, consistent with every other
package added in this project so far.

**Also for step 5.6:** before committing to the full graph shape in 5.11, do a trivial
hello-world compile-and-invoke of a 2-node graph using the pinned version, to confirm the
`StateGraph` construction API, conditional-edge syntax, and `config["configurable"]`
passthrough all behave as this document assumes — cheaper to discover any API mismatch here
than mid-way through writing 5.11's real graph.

---

## Fix 8 — document the REPLAN coarse-graining as intentional

**Add to step 5.3's rationale, verbatim:**

> REPLAN-phase tools (`reoptimize_routes`, `expand_poi_search`) and this doc's `finish_plan`
> deliberately perform multiple internal engine/search steps under one `execute_tool` call —
> this is intentional coarse-graining for recovery actions, not a violation of "nodes only call
> execute_tool," and not an inconsistency with DISCOVER/PLAN's one-primitive-per-call pattern.
> The tradeoff, accepted deliberately: a REPLAN tool's `tool_trace` timing entry represents an
> aggregate of several sub-steps, not one atomic action. If finer-grained REPLAN observability
> is ever needed, record sub-step timings inside `ToolResult.data` rather than emitting
> synthetic additional `tool_trace` entries that would inflate `tool_loop_count` for what is
> conceptually still one logical recovery action.

---

## Minor items to fold in while touching these steps

- Name the currently-unnamed magic numbers: `SEARCH_EXPAND_FACTOR = 1.5` (step 5.3) and a
  `RANK_EXPLANATION_TOP_N = 5` (step 5.2, for how many `explain_selection` strings `rank_places`
  keeps) — both as named constants (in `travel_rules.py` or a small `planner/tools/constants.py`),
  not inline literals, consistent with the "no magic numbers" rule already locked in P4.
- Spell out the exact field mapping from `state.route`/`state.schedule` into
  `travel_engine.TripItinerary`/`DayPlan` (used by `validate_itinerary`) explicitly in step 5.3
  rather than leaving it to be inferred — a one-paragraph "these fields map to these" note is
  enough, but it needs to exist in the doc.

---

## Where each fix lands

| Fix | Step(s) affected |
|---|---|
| 1 — ToolContext via config only | 5.9, 5.12; add to `AGENT.md` planner rules |
| 2 — unified tool execution pathway | 5.9 (rewrite), 5.11 (simplify graph edges) |
| 3 — explicit list-state accumulation | 5.6 (state design note), 5.9 (node implementations) |
| 4 — timeout evaluation gap | 5.12 (rewrite) |
| 5 — tools never mutate state directly | 5.1 (remove ambiguous language), 5.5 (`apply_tool_result` as sole writer) |
| 6 — stuck-detector unconditional rationale | 5.5 (add rationale), 5.9 (implementation) |
| 7 — exact langgraph pin + hello-world check | 5.6 |
| 8 — REPLAN coarse-graining rationale | 5.3 |
| Minor — named constants, state→engine mapping | 5.2, 5.3 |

**Recommended order to apply:** fix `travel_rules.py`/constants (minor items) and the
`langgraph` pin (7) first since they're independent; then rework `ToolContext` and remove the
mutation-callback language (1, 5) since 5.9's rewrite depends on both; then rewrite
`agent_node`/`tool_executor_node` together as one unit (2, 3, 6) since they're the same two
functions; then rewrite `PlannerService.generate` (4); then update step 5.13's tests to cover
all of the above before running the step 5.14 smoke script.