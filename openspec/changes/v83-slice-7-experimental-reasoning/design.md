## Context

See `proposal.md` for why this slice exists. Today `rank_places` calls `rank_candidates` and never calls the gateway. `PlannerService.generate` wraps `graph.ainvoke` in `wait_for(PLANNER_GENERATION_TIMEOUT_SECONDS)` (45), emits one terminal event, then `record_evaluation`. The router saves and caches the dict `generate` returns. `ToolResult.data` for ranking is `ranked_pois` and `explanations`. `apply_tool_result` is the state writer for tool output. `token_usage` is a flat prompt/completion/total dict merged by `merge_token_usage`. `TripEvaluation` already stores `tool_trace` and `token_usage`. Specs that own that model forbid a new column. `chat_completion` is the structured-output gateway, with tenacity retries, `LLM_TIMEOUT_SECONDS` (20), and replay fixtures. The offline judge stays in `src/evaluation/judge/` and is not on this path.

## Goals / Non-Goals

**Goals:**

- Two roles, reasoner then critic, sharing one invocation budget and one per-call deadline.
- Live priorities are a bounded boost inside `rank_candidates` before the rest of the engine runs.
- Shadow compares a copy and leaves the saved trip, the cache blob, and the SSE list on the control path.
- Failure of either role is a named skip, not a 500 and not a second model.
- ADR-013 is filled from a real replay comparison and still leaves the flag default false.

**Non-Goals:**

- A new graph node, a new registry tool, or a repair loop.
- Re-running routing, geocoding, or the agent loop for the shadow copy.
- Changing default `run_evals.py` itinerary gating.

## Decisions

### 1. Roles live in `src/planner/reasoning/`, not in the registry

`schemas.py` holds closed payloads. `experience_reasoner.py` and `critic.py` call `chat_completion` with `response_format` JSON. `budget.py` applies the deadline and the invocation counter. Prompt text sits next to a version constant (`s7-reasoner-1`, `s7-critic-1`). A wording change bumps the constant.

`rank_places` lazy-imports the reasoner only inside the `REASONING_LAYER_ENABLED` branch, so a flag-off ranking path does not call the gateway. The wrapper returns a result object. It does not touch graph state.

Alternative: a new `propose_priorities` tool. Rejected. The blueprint stop line is a tool outside the registry, and a tool the agent can skip would make the experiment optional in the wrong place.

### 2. The engine applies a fixed boost; the model does not rank

`rank_candidates(..., priorities: Mapping[UUID, Literal["high","medium","low"]] | None = None)`. `None` or `{}` keeps today's score, order, and breakdown keys. Weights in `travel_rules.py`: high `0.30`, medium `0.15`, low `0.0`. High is below the smallest positive interest weight (`family` = 0.9), so one priority cannot outrank one interest match. The breakdown key `reasoning_priority` is added only for a place that has a priority. Unknown ids are ignored. The selector still sorts by score, name, id.

Alternative: let the model return a full order. Rejected. N4 says order is not the model's to set, and the order-invariance property would be meaningless if a prompt could reshuffle it.

### 3. Side results travel on `ToolContext`, then flush after the terminal event

Tools may only return `ToolResult`, and ranking `data` cannot grow a diagnostics key. `ToolContext` gains an optional in-memory list, `reasoning_notes`, that is not a graph-state field and is not put in a checkpoint. `rank_places` appends the reasoner note and usage there. After `emit_terminal_from_state`, `generate` flushes notes onto `final["tool_trace"]` as `ToolTraceEntry` rows (`name` `experience_reasoner` or `itinerary_critic`, payload under `diagnostics`, including `mode` of `live` or `shadow`) and merges usage with `merge_token_usage`. Then it runs shadow or the critic, flushes those notes the same way, then calls `record_evaluation`.

`tool_done` has already been emitted for `rank_places` with the existing code, so the client does not see a new event. `itinerary_done` does not include `tool_trace`. The cache subset does not either.

Alternative: a new JSONB column. Rejected. `planner-narrative-evaluation` and `p5-phase-gated-tool-loop` forbid a new `TripEvaluation` column, and `tool_trace` is already the ranking-explanation store.

### 4. Shadow is a copy after the graph wait; live boost is inside it

Flag matrix:

| Layer | Sample selected | What runs |
|---|---|---|
| false | no | Today's graph only |
| false | yes | Graph as today, then reasoner + optional critic on copies. Returned itinerary unchanged |
| true | ignored | Reasoner inside `rank_places`, then the existing engine. Critic after the terminal event if a budget slot remains |

Shadow re-ranks a copy of `candidate_pois` with `rank_candidates`. It does not call `get_routing_provider`, Overpass, or `ainvoke`. The critic reads the control itinerary and the validator findings. Neither calls `on_event`.

The graph `wait_for` stays 45 seconds and does not wrap the shadow or critic. The live reasoner is inside `rank_places`, so it is inside that wait. Its own `asyncio.wait_for` is `min(LLM_TIMEOUT_SECONDS, PLANNER_GENERATION_TIMEOUT_SECONDS // 5)` which is 9 seconds at current settings. On `TimeoutError` or `WandrLLMError` the map is empty and ranking continues. Cancel the inner call. Do not start a different model. The named fallback is `skipped` plus `deadline`, `llm_unavailable`, `malformed`, or `budget`.

`chat_completion` still has its own tenacity retries. The outer deadline is what bounds the user-visible spend. A cancelled call is a skip, not a 500.

Sampling: `SHA-256(f"{session_id}:{destination_id}:{normalized raw_input}")`, first 8 bytes as an unsigned integer, select when `value / 2**64 < rate`. Rate 0 selects none. Rate 1 selects all. No `random` call.

When the invocation cap is 1, the reasoner uses it and the critic records `budget`.

### 5. Cache key suffix only while the layer is on

`build_planner_cache_key` appends `:reasoning-v1` to the hashed material only when `REASONING_LAYER_ENABLED` is true, after the location suffix it already appends. Flag off with an empty location suffix stays the locked MVP string. The router passes the flag the same way it passes `location_suffix`. Shadow does not change the key, because the cached schedule is the control schedule. A cache hit never enters `generate`, so it does not run shadow. That is acceptable: shadow evidence comes from cold generates.

### 6. Ship gate is a separate script and a hand-written ADR

Add `scripts/compare_reasoning.py`. It runs the existing golden itinerary loader twice under `LLM_REPLAY_MODE=replay`, control flags off, treatment layer on, and writes a report under `evals/runs/`. It does not change `scripts/run_evals.py` default behavior and does not update baselines. A missing fixture is a named failure for that case, not a live call.

ADR-013 is written after that report. The margin sentence is in the ADR before the result tables are filled. Human scores come only from `evals/human_review/`. No paired sheets means clause 2 is not met. Unmeasured §4 cells are not met. The settings default stays false in both outcomes. Exit code of the script is non-zero only when the report itself cannot be produced.

### 7. Prompts treat retrieved text as data

System text states the closed schema and forbids new ids, coordinates, and repairs. User text, names, tags, and descriptions are wrapped in explicit untrusted delimiters. The critic is told that deterministic findings are facts it cannot clear. Neither prompt asks for a tool call.

## Risks / Trade-offs

- [Live reasoner sits inside the 45 second wait] → 9 second inner deadline and empty-map fallback. A skip is a successful deterministic rank, not `generation_timeout`.
- [Gateway retries can still burn most of that 9 seconds] → The outer `wait_for` cancels the call. Do not raise `LLM_MAX_RETRIES` for this slice.
- [Shadow keeps the HTTP task open after `itinerary_done` is queued] → The event is already on the queue. Shadow is capped by the same 9 second deadline and at most two calls. Disconnect cancels the generate task, which cancels the shadow await.
- [`tool_trace` gains names that are not registry tools] → Metrics that count tools must ignore names absent from `TOOL_REGISTRY`. `tool_loop_count` is not incremented. Document this in `docs/context.md`.
- [Second `record_evaluation` row] → Already true for the happy path. The flushed trace must be on the state passed to the service-level write so the latest row carries it.
- [Small-model JSON is often invalid] → Schema failure is the designed fallback. The ship gate counts that skip rate and cannot call it a quality win.
- [Golden set and §4 cost are still short] → ADR-013 stays off. This slice does not pretend the entry soak or the judge promotion has happened.
- [Flag-on cache would poison flag-off rollback] → `:reasoning-v1` suffix. Rollback is the flag and the sample rate, not a migration.

## Migration Plan

No Alembic revision. Deploy with both reasoning flags at their defaults. Rollback is `REASONING_LAYER_ENABLED=false` and `REASONING_SHADOW_SAMPLE_RATE=0`, which returns ranking, the cache key, and the SSE list to today's path. Cached reasoned entries become unused because the key no longer matches. They expire by `PLANNER_CACHE_TTL_SECONDS`.

## Open Questions

None. Prompt wording can change only by bumping the version constant. That does not change the schemas or the flag defaults.
