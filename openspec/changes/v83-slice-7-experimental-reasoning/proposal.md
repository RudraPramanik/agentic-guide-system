## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §5.2, §7.1, §9 rows **7.1–7.4**, §11.9, §12) is the next product slice after canonical trips. This is not `docs/steps/step7.md` (P7 edits, already shipped). `docs/context.md` records Slices 5 and 6 as implemented behind flags that stay off. `src/planner/reasoning/` does not exist. Ranking in `rank_places` is still a pure `travel_engine` call. Nothing in the request path can propose place priorities or an advisory critique, and nothing can prove whether those two roles beat the current planner inside the latency and cost bounds. The golden set is still short of the Slice 2 minimum, and the §4 token, cost, and p50 cells are still `[SET IN S0]`.

## What Changes

- Row **7.1**: add an experience reasoner under `src/planner/reasoning/`. It calls `chat_completion` (not `chat_with_tools`), returns priorities only for `place_id`s already in the candidate set, drops unknown ids, and on malformed output, timeout, or gateway failure returns skipped. It is not a registry tool.
- Row **7.2**: add an advisory critic in the same package. It reads the request, search area, evidence refs, the canonical trip, and deterministic findings. It writes structured notes. It cannot change the trip, the validator result, or `validation_passed`, and it cannot start a repair. `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` stays 0 and any other value is rejected at settings load.
- Row **7.3**: add shadow sampling. A request is shadowed only when `REASONING_LAYER_ENABLED` is false, `REASONING_SHADOW_SAMPLE_RATE` is above 0, and a deterministic hash of the request falls inside the rate. Shadow work runs after the terminal SSE event, on copies. It does not call `on_event`, does not change the itinerary that `save_from_state` persists, and does not write a second trip. Live enablement is a different path: the reasoner runs inside `rank_places` before `rank_candidates`, and the published trip is the treatment.
- Row **7.4**: add a replay comparison and ADR-013. The pre-registered human margin is +10 percentage points pass rate, or +0.3 on a 5-point scale, with a confidence interval that excludes zero. That margin is fixed in the ADR before the treatment run. Missing human pairs, an unmeasured §4 cell, or any failed §11.3 gate means the decision is stay off. This change does not set `REASONING_LAYER_ENABLED` to true.
- No **BREAKING** change to HTTP paths, SSE event names, `itinerary_done` fields, GeoJSON, or the preference-cache key while the reasoning flags are at their defaults.

## Capabilities

### New Capabilities

- `experience-reasoner`: typed priority proposal over existing place ids, gateway-only, skip on failure (row 7.1).
- `itinerary-critic`: read-only advisory notes that cannot override a critical finding or trigger repair (row 7.2).
- `reasoning-shadow`: sampled side comparison that cannot persist or change the response (row 7.3).
- `reasoning-ship-gate`: golden replay comparison, pre-registered margin, and ADR-013 with the default flag left off (row 7.4).

### Modified Capabilities

- `planner-discover-tools`: `rank_places` stays free of the gateway when `REASONING_LAYER_ENABLED` is false. When the flag is true it may call the reasoner wrapper, then still ranks with `rank_candidates`.
- `travel-engine-place-selector`: optional non-negative priority boosts. An empty map leaves scores unchanged. The engine still does not call an LLM or read settings.
- `planner-service-sse-bridge`: shadow and critic work happen after the terminal event, outside the graph timeout, and cannot turn a finished graph into `generation_timeout`.
- `planner-cache-backend`: the MVP cache key gains a reasoning suffix only when `REASONING_LAYER_ENABLED` is true. Flag off keeps today's key bytes.
- `planner-sse-generate`: flag-off generate keeps today's SSE event names and does not add reasoning fields to `itinerary_done`.

## Impact

- **Work surface:** `guideagent` only. No frontend change and no parent-vault change. Shadow and the critic do not change the HTTP or SSE contract.
- **Code:** `src/planner/reasoning/**` (new), `src/config.py`, `.env.example`, `src/planner/tools/rank_places.py`, `src/travel_engine/place_selector.py`, `src/travel_engine/travel_rules.py`, `src/planner/service.py`, `src/planner/cache.py`, `src/planner/router.py` (cache-key suffix only), `scripts/run_evals.py` or a sibling comparison script, `docs/v8.2/adr/013-reasoning-layer-ship.md`, `docs/context.md`.
- **Tests:** `tests/planner/reasoning`, planner service integration, place-selector unit tests, cache-key tests, architecture import checks.
- **Settings added, all legacy by default:** `REASONING_LAYER_ENABLED=false`, `REASONING_SHADOW_SAMPLE_RATE=0.0`, `ORCHESTRATION_MAX_AGENT_INVOCATIONS=2`, `ORCHESTRATION_MAX_REPAIR_ATTEMPTS=0`, `AGENT_REASONING_MODEL` empty, `AGENT_CRITIC_MODEL` empty. Empty model settings use `LLM_MODEL`. No new provider and no new API key.
- **No new package, no Alembic revision, no new `TripEvaluation` column, no new HTTP path, no new registry tool.** Reasoning traces are `tool_trace` diagnostics entries named `experience_reasoner` and `itinerary_critic`. They do not increment `tool_loop_count`. Their token counts merge into the existing `token_usage` dict through `merge_token_usage`.
- **Status note:** `docs/context.md` still lists golden-case expansion as an open Slice 1–4 gap. This change does not close that gap, does not promote the offline judge, and does not claim the §11.9 ship gate has passed.

## Non-goals

- No third role, hotel agent, photo agent, or supervisor. Slice 9 stays out of this change.
- No in-path repair loop and no critic-triggered replan. `ORCHESTRATION_MAX_REPAIR_ATTEMPTS` cannot be set above 0.
- No use of `src/evaluation/judge/` on the request path. `EVALUATION_JUDGE_ENABLED` stays false and this slice does not change the offline judge.
- No second LLM gateway and no `litellm` import outside `src/core/llm/client.py`.
- No change to stop ids, coordinates, order, times, prices, or opening hours coming from the model (N4). Priorities are non-negative boosts on places the retriever already returned. Omission means no opinion, not a ban.
- No new SSE event, no new `itinerary_done` field, and no reasoning payload in `tool_done`.
- No flip of `REASONING_LAYER_ENABLED` or any earlier slice flag. Enabling the layer in production is a later change that may open only after ADR-013 records that §11.9 passed.
- No invented human scores and no `--update-baseline` of the itinerary golden baseline.

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Call models only through `chat_completion` (G1). The reasoner and critic do not register tools and do not use `chat_with_tools` (row 7.1 stop line).
- Keep `src/travel_engine/**` free of LLM, network, DB, and settings reads (G2). The tool passes a priority map in. An empty map is the flag-off path (G13).
- Read flags only through `get_settings()` (G3, G11). Defaults stay off. `tests/architecture/_helpers.py` already expects these two reasoning defaults.
- Leave deterministic critical findings in force (N3, ADR-004). The critic cannot clear `blocks_publish` or `validation_passed`.
- Record the model actually called and a named skip reason. Do not swap to a second model on failure (N10).
- Keep `PLANNER_GENERATION_TIMEOUT_SECONDS` at 45. Do not raise it. Shadow work is outside that wait and cannot rewrite a successful graph result into `generation_timeout`.
- Treat retrieved text, tags, and the user request as untrusted. Delimit them in the prompt. No tool, SQL, or shell authority for either role (§15).
- Keep flag-off generate replay and the flag-off cache key identical to today (G8, G13).

## Decisions

The blueprint's per-row path list cannot both keep the reasoner out of the tool registry and let a deterministic scorer apply priorities. These seams are in scope:

1. `rank_places` is the only tool edit. It calls the wrapper only when the layer flag is true, then calls `rank_candidates` as it does today. Flag off does not import a call to the gateway.
2. `place_selector` and `travel_rules` gain an optional boost. Weights are fixed constants, smaller than one interest-tag weight, so a priority cannot replace interest matching. The engine does not import `src.planner.reasoning`.
3. The preference-cache key grows a suffix only while the layer flag is true, using the same pattern as the location suffix, so a reasoned trip is not replayed after rollback and a flag-off key does not change.
4. Shadow sampling uses a stable hash, not `random.random()`, so replay selects the same requests.
5. Each role call is capped with `asyncio.wait_for` at `min(LLM_TIMEOUT_SECONDS, PLANNER_GENERATION_TIMEOUT_SECONDS // 5)` (9 seconds at today's settings). On timeout the role is skipped. The invocation cap counts only these two roles, not the existing agent loop. When the cap is 1, the reasoner keeps the slot and the critic is skipped.
6. ADR-013 is written from the comparison that this change actually runs. Absent human-review pairs fail clause 2 of §11.9 closed. That outcome is valid. The flag default stays false either way.
