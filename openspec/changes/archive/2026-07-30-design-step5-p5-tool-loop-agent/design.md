## Context

P0–P4 are done: core infra, auth, geo seed, enrichment/Qdrant, pure `travel_engine` + CORS + `OsrmRoutingProvider` + thin `ToolResult`/`execute_tool` stub. Planner graph nodes, tool bodies, evaluation service, and `planner/service` SSE bridge remain **stubs** (~1-line placeholders) — do not assume APIs exist beyond the P4 envelope.

`docs/blueprint_final.md` **v6.1** is Planner SoT (principles 6–13, AGENT.md, Resilience Contracts, `planner/tools` design, Phase-Gated Tool Loop, P5 5.1–5.14). `docs/steps/step5.md` is empty. P2–P4 succeeded because hardened step prompts locked contracts before Cursor apply. This design change authors that P5 prompt (and OpenSpec alignment), not the production agent code itself.

Already shipped (do not reinvent):
- `src/core/llm/client.py` — `chat_completion` + `chat_with_tools` + `LLMToolResponse` (P0)
- `src/planner/routing_provider.py` — `OsrmRoutingProvider`
- `src/planner/tools/schemas.py` — `ToolResult` only
- `src/planner/tools/registry.py` — unknown → `ok=False`
- Planner settings: `PLANNER_MAX_TOOL_CALLS`, `PLANNER_MAX_REPLAN_ATTEMPTS`, `PLANNER_GENERATION_TIMEOUT_SECONDS`, `PLANNER_MIN_READINESS_SCORE`, `PLANNER_AGENT_PHASE_STUCK_LIMIT`
- `langgraph` is **not** in `requirements.txt` yet (blueprint installs at graph step)

Constraints (AGENT.md): tools only via `execute_tool`; LLM only via `core/llm/client.py`; nodes never call tool impls; travel_engine stays pure; evaluation never skipped; all env via `get_settings()`.

## Goals / Non-Goals

**Goals:**

- Author `docs/steps/step5.md` in the **step2/step4 shape**: Decision/Fix log, prerequisites, architecture, locked decisions, sub-steps **5.1–5.14**, FAILURE BOUNDARY per code step, ✅ validation, pytest plan, smoke/real proof, ship checklist.
- Encode blueprint_final v6.1 locks: `AgentPhase` / `PHASE_TOOLS`, deterministic transitions, 12 typed tools, `ToolContext` outside `TravelState`, bounded ReAct, no-tool nudge, narrative cannot mutate geometry, evaluation always written, service SSE event bridge.
- Clarify blueprint numbering quirks in the prompt (e.g. “core six” vs listed bullets; `chat_with_tools` already exists; package install timing).
- Define **batched OpenSpec implementation clusters** so multiple sub-steps ship per apply for speed.

**Non-Goals:**

- Implementing production planner/tools/graph code in *this* change’s apply — primary apply = write the prompt.
- P6 HTTP `POST /planner/generate`, trips CRUD persistence, Redis cache, absolute min-places HTTP floor.
- P7 edit/replan API.
- Turning `blueprint_final.md` into a Cursor prompt or backfilling the whole blueprint into OpenSpec main specs.
- One OpenSpec propose→apply→archive ceremony per micro-step during implementation.

## Decisions

### D0 — Process: blueprint vs step prompt vs OpenSpec cadence

**Choice:** Keep three layers distinct:

| Layer | Role |
|-------|------|
| `docs/blueprint_final.md` | Product/architecture SoT |
| `docs/steps/step5.md` | Agent build contract (sub-steps, validation, tests) |
| OpenSpec change | Propose → apply → archive for *batches* of work |

**Apply cadence for P5 implementation (after this design change archives):** Prefer **one design change now**, then **batched implementation changes**:

1. `5.1–5.3` — schemas/registry + all 12 tool bodies (discover → plan/validate → control/replan)
2. `5.4–5.5` — verify/harden `chat_with_tools` + phase gating / preconditions / transitions / tool_trace
3. `5.6–5.8` — TravelState + messages + `parse_preferences` (+ install `langgraph` at 5.6)
4. `5.9–5.11` — agent + tool_executor + narrative/eval + graph compile
5. `5.12–5.14` — service SSE bridge + pytest tool-loop + `scripts/test_agent.py` + context.md

Do **not** run full propose→archive for every micro-step; `step5.md` already locks the contract.

### D1 — Tool split vs blueprint “core six” title

**Choice (LOCKED in prompt):** Treat the **12-tool registry** as the unit of truth. Numbering:

| Step | Tools |
|------|-------|
| 5.1 | Schemas + `AgentPhase` + `ToolContext` + `PHASE_TOOLS` + register all 12 (stubs OK until bodies land) |
| 5.2 | DISCOVER: `check_readiness`, `search_places`, `rank_places` |
| 5.3 | PLAN+VALIDATE+control+replan: `build_route`, `build_schedule`, `validate_itinerary`, `finish_plan`, `ask_clarification`, `reoptimize_routes`, `drop_weakest_stop`, `expand_poi_search`, `accept_partial` |

Blueprint’s “core six” label under 5.2 is clarified in the Decision Log as discover(3)+plan(2)+validate(1) conceptually, but **implementation order keeps build/validate in 5.3** so 5.2 can land and be tested before routing-heavy tools.

### D2 — `ToolContext` NOT in LangGraph `TravelState`

**Choice:** `AsyncSession` and `RoutingProvider` live on `ToolContext`, threaded via closure / `RunnableConfig.configurable`. Never embed non-serializable deps in the TypedDict checkpointed by LangGraph.

**DB lifecycle (LOCKED preference):** acquire `AsyncSession` inside tools that need DB (`search_places` PostGIS fallback, evaluation write, future trip save). Prefer not holding one session for the full 45s generation.

### D3 — Phase transitions are deterministic (never LLM-chosen)

Encode the blueprint transition table verbatim in the prompt. `maybe_transition_phase(state, tool_name, result)` is the only mutator of `agent_phase` besides ceiling/abort paths in the agent node.

### D4 — Bounded agent loop + no-tool nudge

- `tool_loop_count >= PLANNER_MAX_TOOL_CALLS` → `abort_triggered=True`, force `WRAP_UP`.
- No tool call: system nudge → one retry `tool_choice="required"` → else default tool for phase (DISCOVER → `check_readiness`); record in `tool_trace`.
- Same phase, no state change × `PLANNER_AGENT_PHASE_STUCK_LIMIT` → auto-advance or abort (prompt locks the exact rule).
- `WandrLLMError` in agent → execute default tool for phase once; increment `llm_retry_count`.

### D5 — Structure from code, narrative from LLM

`write_narrative` runs **outside** the tool loop after `plan_complete`. It may only produce day titles + paragraphs. Post-check: every `place_id` referenced must already exist in schedule; LLM cannot add/reorder stops or invent times. On LLM failure → template strings; never block evaluation.

### D6 — `finish_plan` precondition

`finish_plan` MUST NOT succeed until `validate_itinerary` returned `ok=True` **OR** `state.abort_triggered=True`. Wrong-phase / unmet precondition → `ToolResult(ok=False, code="precondition_failed")` — never raise.

### D7 — REPLAN prefers expand when PLAN already dropped stops

If a day already has `dropped_stops` from route_optimizer drop-retry, agent messages MUST prefer `expand_poi_search` over `drop_weakest_stop`. Prompt locks this in `messages.py` system/REPLAN guidance.

### D8 — `chat_with_tools` already exists (P0)

Step 5.4 is **verify + test harden**, not a greenfield add: confirm schema passthrough, content-only handling, same tenacity contract as `chat_completion`. Add/extend unit tests with mocked LiteLLM. Do not re-install litellm.

### D9 — Package: `langgraph` at 5.6

Install `langgraph` with requirements.txt why-comment when TravelState/graph work begins (blueprint table says 5.6). Builder (5.11) consumes it. No other new packages without justification.

### D10 — SSE bridge in P5 service; HTTP router in P6

Step 5.12 implements **planner/service.py** event emission hooks (`tool_started` / `tool_done` / `phase_changed`) + `asyncio.wait_for(..., PLANNER_GENERATION_TIMEOUT_SECONDS)` around graph invoke. Full `POST /api/v1/planner/generate` StreamingResponse, disconnect cancel, queue design, and absolute min-places pre-graph floor are **P6** — forward-locked in Decision Log only.

### D11 — Evaluation always recorded

`record_evaluation` always runs (including abort / clarification exit paths that still produce a generation attempt). Persist `tool_trace`, `tool_loop_count`, `agent_phase_reached`, resilience flags. `explain_selection` / ranking rationales stay in `tool_trace` — no new TripEvaluation column.

### D12 — Prompt build order (locked)

```
5.1 schemas + registry (12 tools registered)
  → 5.2 DISCOVER tools
    → 5.3 PLAN/VALIDATE/control/replan tools
      → 5.4 verify chat_with_tools + tests
        → 5.5 phase gating + preconditions + transitions + tool_trace
          → 5.6 TravelState (+ langgraph install)
            → 5.7 messages / agent prompt
              → 5.8 parse_preferences
                → 5.9 agent + tool_executor
                  → 5.10 write_narrative + record_evaluation
                    → 5.11 graph builder compile
                      → 5.12 service SSE bridge
                        → 5.13 pytest tool_loop
                          → 5.14 scripts/test_agent.py + context.md
```

### D13 — Design patterns called out in the prompt

| Module | Pattern | Meaning in P5 |
|--------|---------|----------------|
| `tools/registry` | Registry + Command | Named tools only; execute via one entry point |
| `AgentPhase` / `PHASE_TOOLS` | State machine | Phase gating; LLM never chooses phase |
| `ToolContext` | Context Object / DI | Non-serializable deps outside checkpointed state |
| `agent` ↔ `tool_executor` | Bounded ReAct loop | Ceiling + phase tools + validate-before-finish |
| `write_narrative` | Fixed bookend | LLM narrative only; geometry immutable |
| `OsrmRoutingProvider` | Adapter (from P4) | Injected into ToolContext.routing |

### D14 — Verification bar (match step4 quality)

Every code step: import/unit proof. Phase closeout: `tests/planner/test_tool_loop.py` (5.13) + `scripts/test_agent.py` (5.14). Import guards: no litellm outside `core/llm/client.py`; no direct tool fn imports in `planner/graph/nodes/` — only `execute_tool`; travel_engine still pure. Failures: non-zero exit + clear section headers (no ambiguous PASS).

## Risks / Trade-offs

- [Risk] Doc drift if blueprint edits without step5 update → Mitigation: step5 cites blueprint section anchors; context.md points agents at step5 for build.
- [Risk] Holding DB session across LLM latency exhausts pool → Mitigation: D2 per-tool session acquire.
- [Risk] Agent invents place IDs / times → Mitigation: tools + travel_engine own geometry; narrative post-check; system prompt hard rules.
- [Risk] Unbounded tool loops → Mitigation: `PLANNER_MAX_TOOL_CALLS` + stuck detector + replan ceiling.
- [Risk] Over-process OpenSpec per micro-step → Mitigation: D0 batched applies.
- [Risk] Premature HTTP SSE work bloating P5 → Mitigation: D10 — service bridge only; router is P6.
- [Trade-off] Blueprint 5.2 title “core six” vs three bullets → Clarified in D1; prompt Decision Log wins for implementers.
- [Trade-off] Smoke may need live LLM + seeded Darjeeling → Mitigation: pytest mocks LLM; smoke documents required env/keys; fail loud by section.

## Migration Plan

1. Apply this change: write hardened `docs/steps/step5.md` (+ keep OpenSpec artifacts coherent).
2. Archive `design-step5-p5-tool-loop-agent`.
3. Implement from the prompt in batched OpenSpec applies (clusters in D0).
4. After 5.13/5.14 pass: update `docs/context.md`; adjust stubs list; mark P5 progress ✅; Next step → P6.1.
5. Rollback of code later: revert planner/tools/graph/evaluation modules; remove `langgraph` if unused; keep P4 envelope intact.

## Open Questions

None blocking for authoring the prompt. Defaults above (D1–D12) are locked for `step5.md` unless the user overrides before apply.
