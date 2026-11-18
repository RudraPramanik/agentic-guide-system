## 1. Settings and deterministic boost

- [x] 1.1 Add `REASONING_LAYER_ENABLED` (false), `REASONING_SHADOW_SAMPLE_RATE` (0.0), `ORCHESTRATION_MAX_AGENT_INVOCATIONS` (2), `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` (0), `AGENT_REASONING_MODEL` (empty), and `AGENT_CRITIC_MODEL` (empty) to `Settings` and `.env.example`. Reject a sample rate outside 0..1, a negative invocation cap, and any repair-attempt value other than 0. Empty model strings mean `LLM_MODEL`. Do not change `PLANNER_GENERATION_TIMEOUT_SECONDS`.
- [x] 1.2 Add `SCORE_W_PRIORITY_HIGH=0.30`, `SCORE_W_PRIORITY_MEDIUM=0.15`, `SCORE_W_PRIORITY_LOW=0.0`, and breakdown key `reasoning_priority` in `travel_rules.py`. Extend `rank_candidates` / `select_places` with an optional priority map that defaults to empty. Empty map: same scores, order, and breakdown keys as today for V2 off and V2 on. High stays below the smallest positive `CATEGORY_WEIGHTS` value. The engine must not import `src.planner` or an LLM client.
- [x] 1.3 Add unit tests: empty map matches today's scores; a high priority cannot outrank a single interest match; unknown ids are ignored; `low` adds nothing. Run `pytest tests/travel_engine -k selector -v`.

## 2. Experience reasoner (7.1)

- [x] 2.1 Add `src/planner/reasoning/` with closed Pydantic payloads, prompt text beside version `s7-reasoner-1`, and a wrapper that calls `chat_completion` only. Delimit user text, names, tags, and descriptions as untrusted data. Drop unknown ids, duplicate ids after the first, and any item that carries coordinates, order, time, price, or availability. Do not register a tool and do not increment `tool_loop_count`.
- [x] 2.2 On malformed JSON, schema failure, `WandrLLMError`, missing replay fixture, or `asyncio.wait_for` past `min(LLM_TIMEOUT_SECONDS, PLANNER_GENERATION_TIMEOUT_SECONDS // 5)`, return skipped with a named reason and the requested model. Do not call a second model. A skipped result is an empty priority map.
- [x] 2.3 Cap reasoner plus critic calls at `ORCHESTRATION_MAX_AGENT_INVOCATIONS`, not counting the existing agent loop. When the cap is 1, the reasoner keeps the slot.
- [x] 2.4 Add failure-path tests under `tests/planner/reasoning`: unknown id dropped, coordinate item dropped, malformed payload skipped, gateway error does not swap models, deadline skip, registry does not contain the reasoner, package does not import `litellm`. Run `pytest tests/planner/reasoning -v`.

## 3. Advisory critic (7.2)

- [x] 3.1 Add the critic in `src/planner/reasoning/` with prompt version `s7-critic-1`. Input is a copy of the request, search area, evidence refs, canonical itinerary, and deterministic findings. No database session, routing provider, or tool executor. Output notes use only `relevance`, `diversity`, and `narrative`, with stance `pass`, `fail`, or `unknown`, plus model, prompt version, and rubric version.
- [x] 3.2 Drop any note that sets `blocks_publish`, a repair action, or a finding severity. A malformed payload or missing version skips the critic. The critic must not import `src.evaluation.judge` and must not change `validation_passed` or critical findings.
- [x] 3.3 Add tests: a critic pass leaves `DUPLICATE_STOP` and `validation_passed` in place; a repair note is dropped and no replan starts; a timeout records a skip and does not emit SSE. Run `pytest tests/planner/reasoning -k critic -v`.

## 4. Live ranking and trace flush

- [x] 4.1 Add an optional `reasoning_notes` list on `ToolContext` (not on graph state). `rank_places` calls the reasoner only when `REASONING_LAYER_ENABLED` is true, lazy-imports it inside that branch, passes the accepted map into `rank_candidates`, and stores the note plus usage on the context. `ToolResult.data` stays `ranked_pois` and `explanations`. Flag off does not call the gateway. V2 off still skips the normalizer.
- [x] 4.2 After `emit_terminal_from_state` and outside the graph `wait_for`, flush notes onto `tool_trace` as entries named `experience_reasoner` or `itinerary_critic` and merge usage with `merge_token_usage`. Then call the existing `record_evaluation`. A critic or shadow failure must not set `generation_timeout` or `abort_triggered` on a finished graph.
- [x] 4.3 When the layer flag is true and a budget slot remains, run the critic after the terminal event on a copy. It must not call `on_event` and must not change itinerary, schedule, route, ranked places, or validator result.
- [x] 4.4 Add tests: flag off ranking does not call `chat_completion`; layer on with a valid priority returns only `ranked_pois` and `explanations`; a reasoner failure still returns those fields from the unboosted rank; flags off make `generate` skip both roles. Run `pytest tests/planner -k "rank or reasoning" -v`.

## 5. Shadow mode (7.3)

- [x] 5.1 Select shadow requests with SHA-256 of `session_id`, `destination_id`, and whitespace-normalized text (first 8 bytes over 2**64, compared with the rate). Rate 0 selects none. Rate 1 selects all. The same inputs select the same requests. Layer true ignores the sample rate.
- [x] 5.2 After the terminal event, on copies, call the reasoner and re-rank with `rank_candidates`. Do not call the graph, a geocoder, or a routing provider. Do not change the dict fields `save_from_state` uses for the itinerary. Do not write a second trip. Do not call `on_event`. Share the invocation cap and the 9-second deadline. Disconnect cancels the in-flight pass.
- [x] 5.3 Record shadow diagnostics with `mode=shadow`, including skip reasons. An unsampled flag-off generate appends neither reasoning trace entry and does not change `token_usage`. A sampled pass merges tokens for calls that actually ran.
- [x] 5.4 Add an integration test: shadow ranking that orders places differently still emits the control `itinerary_done` and passes the control itinerary to save; a shadow timeout does not mark a `plan_complete` result as `generation_timeout`; the event list gains no shadow event. Run `pytest tests/planner -k shadow -v`.

## 6. Cache key and stream contract

- [x] 6.1 When `REASONING_LAYER_ENABLED` is false, `build_planner_cache_key` stays today's material, including the existing location suffix when that suffix is non-empty, and adds no `:reasoning-v1`. When the flag is true, append `:reasoning-v1` after that material. Wire the suffix from the generate router the same way as the location suffix. Shadow must not change the key.
- [x] 6.2 Add tests: flag off with no location suffix matches the locked MVP hash; flag on and flag off for the same body do not share a key; whitespace-only raw input still collides when the flag is off. Confirm `itinerary_done` gains no reasoning field and `tool_done` stays `name`, `ok`, `code`, `ms`. Run `pytest tests/planner -k "cache or sse" -v`.

## 7. Ship decision (7.4)

- [x] 7.1 Add `scripts/compare_reasoning.py` that loads the existing golden itinerary cases, runs control (`REASONING_LAYER_ENABLED` false, sample rate 0) and treatment (layer true) in replay mode, and writes a report under `evals/runs/`. Do not change the default `run_evals.py` gate and do not pass `--update-baseline`. A missing treatment fixture is a named miss and must not call the provider.
- [x] 7.2 Read human-review sheets that already exist. Do not invent scores. If no paired control-versus-treatment review exists, mark §11.9 clause 2 not met. Treat any `[SET IN S0]` token, cost, or p50 cell as not met.
- [x] 7.3 Run the comparison and write `docs/v8.2/adr/013-reasoning-layer-ship.md` with context, decision, alternatives, consequences, migration, rollback, and status. Put the margin (+10 percentage points or +0.3 on a 5-point scale, interval excluding zero) in the ADR before filling result numbers. Decide stay off unless every ship clause passes. Leave `REASONING_LAYER_ENABLED` false in settings and `.env.example` either way. Rollback text is both flags back to defaults.

## 8. Proof and status

- [x] 8.1 Add an architecture check that `src/planner/reasoning/` does not import `litellm`, `groq`, or `openai`, and that `src/travel_engine/**` does not import `src.planner.reasoning`. Confirm the existing flag-default test still sees the two reasoning defaults off. Run `pytest tests/architecture -v`.
- [x] 8.2 Run `pytest tests/planner/reasoning tests/travel_engine -k "selector or rank" -v` and the shadow test from 5.4. Flag-off generate must not call the reasoner. Do not raise the 45 second ceiling.
- [x] 8.3 Update `docs/context.md` with verified facts only: the package exists, both flags default off, shadow does not persist a treatment, and ADR-013's actual decision. Do not claim the §11.9 ship gate passed unless the report shows every clause met.
