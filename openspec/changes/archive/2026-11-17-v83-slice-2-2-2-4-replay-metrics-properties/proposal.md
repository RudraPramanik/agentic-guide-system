## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **2.2**, **2.3**, and **2.4**, plus §11.1, §11.5, and §11.6) is the next Slice 2 work after the golden schema. There is no `docs/steps/step*.md` for these rows. Subslice 2.1 is archived. `docs/context.md` still names Slice 2 as the next blueprint slice. The gateway in `src/core/llm/client.py` always calls LiteLLM. `scripts/run_evals.py` has no `--replay` flag. `src/evaluation/` has scorers and no metrics package. `tests/travel_engine/` has example tests and no §11.6 property suite.

The user asked for rows 2.2, 2.3, and 2.4 in one change, applied in that order. The blueprint's "one PR per subslice" rule is overridden for this batch only. Each row's stop condition still applies inside the change. Later rows use earlier rows' contracts and do not redefine them.

## What Changes

- Add `LLM_REPLAY_MODE` on `Settings`, default `off`. The closed set is `off`, `replay`, and `record`. `off` keeps today's provider calls. This name is not in §7.1. Row 2.2 requires a setting, and §7.2 says to add a setting only when this slice uses it.
- At the three gateway entry points (`chat_completion`, `chat_with_tools`, `embed_texts`), honor that mode. `replay` returns a committed fixture and does not call LiteLLM. `record` calls LiteLLM once and writes the fixture. A missing fixture in `replay` fails with a named error. `litellm` stays imported only in `src/core/llm/client.py`.
- Add `--replay` on `scripts/run_evals.py`. Two consecutive `--replay` runs produce the same per-case verdicts and reasons. The flag forces replay for that process. It does not read or write `os.environ`.
- Add pure metric functions for location, retrieval recall@k, duplicates, geographic coherence, feasibility, preference, persistence, and map/itinerary consistency. Unit tests use hand-computed expectations. `score_case` verdict rules stay as they are.
- Add §11.6 property tests under `tests/travel_engine/`. The coherence property calls the metric from 2.3. A property that fails on the current engine is recorded as a finding. The engine is not edited to make it pass. `normalize` and `SearchArea` do not exist yet, so those two properties are named skips, not new engine modules.
- No **BREAKING** HTTP, SSE, or persisted-trip change. Mode `off` is the current gateway contract.

## Capabilities

### New Capabilities

- `llm-record-replay`: gateway record and replay, fixture files under `evals/replay/`, and the named miss error. Mode `off` is unchanged.
- `eval-deterministic-metrics`: the eight pure metrics and their hand-computed tests. They do not change pass/fail.
- `travel-engine-properties`: the §11.6 suite, the shared coherence call into the 2.3 metric, and the finding rule when a property fails on today's engine.

### Modified Capabilities

- `llm-chat-with-tools`: the pass-through to LiteLLM applies when `LLM_REPLAY_MODE` is `off` or `record`. `replay` returns the fixture and does not call the provider. The tool-call parse shape is unchanged in every mode.
- `eval-golden-harness`: `--replay` runs the existing suite against fixtures and is identical twice. Schema v2, assertion keys, quarantine, baseline diff, and `score_case` stay as subslice 2.1 left them.

## Impact

- **Work surface, in order:** 2.2 `src/core/llm/client.py`, `src/config.py`, `evals/replay/**`, `scripts/run_evals.py`, `tests/core/**`; then 2.3 `src/evaluation/metrics/**`, `tests/evaluation/**`; then 2.4 `tests/travel_engine/**`. `src/evaluation/scorers.py` is in the 2.3 path cell and is not required to change.
- **Call sites outside a row path cell:** `src/config.py` holds the setting because rollback is "setting off" and G3 forbids `os.environ` elsewhere. `.env.example` gains `LLM_REPLAY_MODE=off` beside the LLM settings it already lists. `scripts/run_evals.py` grows `--replay` because that is row 2.2's verify command. `tests/core/**` and `tests/evaluation/**` hold the tests those verify commands cannot see from the path cell alone. This is the same kind of wiring 2.1 used for the loader. No other file outside those sets is in scope.
- **No new package.** No `requirements.txt` change. No `hypothesis`. No HTTP route. No migration.
- **Resilience:** mode `off` keeps the existing LiteLLM timeout and tenacity retry. `replay` does not call the provider, so it adds no timeout. A miss is the named fallback, not a hang. `record` uses the existing timeout and retry, then writes the fixture.
- **No impact on:** planner generate when the mode is `off`, SSE event names, trip persistence, golden schema, baseline update, CI workflows, the travel engine source, and `docs/context.md`.
- **Downstream:** 2.5 owns tolerance bands, `--update-baseline` changes, quarantine exclusion from the gate, and the CI job. 2.6 owns the judge. Slice 3 owns `SearchArea`. Slice 4 owns `candidate_normalizer` and `TRAVEL_ENGINE_V2_ENABLED`.

## Non-goals

- No edit to `.github/workflows/**`, no change to baseline tolerance, and no dropping of quarantined cases (subslice 2.5). `--update-baseline` and `--fixtures-only` stay as they are.
- No `src/evaluation/judge/**` and no `EVALUATION_JUDGE_ENABLED` (subslice 2.6).
- No new assertion key and no change to how `score_case` decides pass or fail.
- No edit under `src/travel_engine/**`. A failing property is a finding (row 2.4 stop condition).
- No `candidate_normalizer.py`, no `SearchArea`, and no `TRAVEL_ENGINE_V2_ENABLED`. Those properties are skipped with a stable reason until the slice that owns the type.
- No second LLM client and no provider SDK import outside `src/core/llm/client.py` (row 2.2 stop condition).
- No new destination and no new golden file. The twelve Darjeeling cases stay.
- No edit to `docs/context.md`. None of the three rows list it. The §19 completion report goes in the PR description.

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep `litellm` imported only in `src/core/llm/client.py`.
- Read the mode through `get_settings()`. The eval script must not call `os.environ`.
- Keep metric functions and property tests free of LLM, network, and database I/O.
- Leave `src/travel_engine/**` source unchanged. Routing in a property test uses the existing `FakeRoutingProvider` where a test calls `optimize_route`.
- Add no package. Defaults stay `off`, which is today's behavior.
- Apply 2.2, then 2.3, then 2.4. 2.4 imports the coherence function 2.3 defined. It does not copy a second formula.

Blueprint path notes, confirmed against the checkout rather than treated as a halt:

- The gateway, scorers, and travel engine are real modules. Evaluation HTTP is still a stub and is not called.
- `evals/replay/` does not exist yet. Row 2.2 creates it.
- `src/evaluation/metrics/` does not exist yet. Row 2.3 creates it. The coherence formula is the one already documented on `trip_validator._day_coord_stddev_km` (sample dispersion in local km). The metric reimplements that definition. It does not import or edit `trip_validator.py`, because that file is outside 2.3's allowed paths.
- Tests for 2.2 belong in `tests/core/**` because the gateway tests already live there. Tests for 2.3 belong in `tests/evaluation/**` because the verify command is `pytest tests/evaluation -v`.
