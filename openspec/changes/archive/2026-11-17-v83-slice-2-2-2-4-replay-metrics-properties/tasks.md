## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §9 rows 2.2, 2.3, and 2.4 and §11.6, plus this change's `proposal.md`, `design.md`, and the five delta specs. There is no `docs/steps/step*.md` for these rows. Do not start 2.3 until section 2 is green, and do not start 2.4 until section 3 is green.
- [x] 1.2 Confirm the gateway, `src/evaluation/scorers.py`, and `src/travel_engine/` are real modules. Do not call the evaluation HTTP stub. Do not add a package, a migration, or a workflow file.

## 2. Slice 2.2 — record and replay

- [x] 2.1 Add `LLM_REPLAY_MODE: str = "off"` on `Settings` with a validator that accepts only `off`, `replay`, and `record`. Add `LLM_REPLAY_MODE=off` in `.env.example` beside the existing `LLM_*` lines. Do not edit `tests/architecture/_helpers.py`.
- [x] 2.2 In `src/core/llm/client.py`, add a `ContextVar` and `use_llm_replay(mode)`. The effective mode is the context value when set, otherwise the setting. Check it at the start of `chat_completion`, `chat_with_tools`, and `embed_texts`, before the retried inner call.
- [x] 2.3 Implement the fixture id as the hex SHA-256 of canonical JSON (`operation`, `model`, payload) with `sort_keys=True`, compact separators, and `ensure_ascii=False`. Store files at `evals/replay/<id>.json`. Do not store the API key. Timestamps and retry bookkeeping are not part of the id.
- [x] 2.4 `replay` loads the fixture and returns the existing result type (`ChatCompletionResult`, `LLMToolResponse` with `{name, arguments_json}`, or `list[list[float]]`). It does not call LiteLLM and does not sleep. A miss raises `WandrLLMError` with code `replay_miss` and the fixture id in the message.
- [x] 2.5 `record` uses the existing timeout and tenacity path, writes the fixture only after success, and returns that result. `off` stays the current path. `litellm` remains imported only in this module.
- [x] 2.6 Add `--replay` to `scripts/run_evals.py`. It calls `use_llm_replay("replay")` and does not read or write `os.environ`. It does not change `--update-baseline`, `--fixtures-only`, baseline files, or `score_case`.
- [x] 2.7 Add gateway tests for: default mode `off` still calls a mocked provider; the same payload replayed twice matches and does not call the provider; a tool fixture keeps name and argument string; an embedding fixture keeps the vectors; a missing fixture raises `replay_miss`; record-then-replay calls the provider once. Use a temp replay directory.
- [x] 2.8 If `LLM_API_KEY` is non-empty, record the Darjeeling suite once and commit `evals/replay/**`. If the key is empty, stop and report. Do not invent fixture bodies.
- [x] 2.9 Run `python scripts/run_evals.py --replay` twice and confirm the per-case verdicts and reasons match and the provider is not called. Confirm a forced miss exits non-zero and prints `replay_miss`.

## 3. Slice 2.3 — metrics

- [x] 3.1 Do not start this section until task 2.9 has passed. Do not import the gateway from `src/evaluation/`.
- [x] 3.2 Add `src/evaluation/metrics/__init__.py` with `location_type_accuracy`, `retrieval_recall_at_k`, `duplicate_stop_count`, `geographic_coherence_km`, `schedule_feasibility`, `preference_match`, `persistence_match`, and `map_itinerary_match`, matching the signatures in `design.md`. Empty inputs return the spec's `1.0` or `0` cases. No LLM, network, or database call.
- [x] 3.3 Implement `geographic_coherence_km` as the validator dispersion (local-km offsets, sample variance over `n - 1`, square root of the sum) using `111.0`. Fewer than two coordinates returns `None`. Do not import or edit `trip_validator.py`.
- [x] 3.4 Leave `src/evaluation/scorers.py` unchanged. Do not add an assertion key.
- [x] 3.5 Add `tests/evaluation/test_metrics.py` for the hand-computed spec cases, including location `2/3`, recall `0.5` and the repeated-id `1.0`, duplicate counts `1` and `0`, coherence `None` and `0`, the farther point scoring strictly higher, feasibility `0.5` and `1.0`, preference `0.5`, persistence match and reorder mismatch, and map match and extra-feature mismatch.
- [x] 3.6 Run `pytest tests/evaluation -v` and confirm exit 0. Confirm a Darjeeling case still scored by `score_case` keeps its verdict.

## 4. Slice 2.4 — property tests

- [x] 4.1 Do not start this section until task 3.6 has passed. Do not edit any file under `src/travel_engine/`.
- [x] 4.2 Add `tests/travel_engine/test_properties.py`. Determinism and order invariance call `select_places` and `allocate_days`. The shuffle compares the selected set and day membership. Removal drops one stop on a fixture `TripItinerary` and checks unique ids and non-decreasing start times. Do not add a remove API.
- [x] 4.3 The monotonic-coherence test imports `geographic_coherence_km` from `src.evaluation.metrics` and asserts the kilometer value does not decrease after a farther point is added. Do not copy the dispersion formula into the test.
- [x] 4.4 Budget checks allocator output against `ACTIVE_DAY_VISIT_BUDGET_MIN` and `MAX_PLACES_PER_DAY`. Schedule checks `build_day_schedule` start times are strictly increasing, and a scheduled duration equals the matching `RouteLeg` when a leg exists. Use `tests/travel_engine/fake_routing.py` where routing responses are required.
- [x] 4.5 Scan `src/travel_engine/**/*.py` and fail if `TRAVEL_ENGINE_V2_ENABLED` appears. Do not add that setting. Skip idempotent dedup with reason `slice 4.1 owns candidate normalizer`. Skip area respect with reason `slice 3 owns SearchArea`. Do not create those modules.
- [x] 4.6 If a property fails on the current engine, add a named row to `tests/travel_engine/PROPERTY_FINDINGS.md` and mark that test `pytest.mark.xfail(reason="finding: <property>", strict=True)`. Do not edit the engine to make it pass. If none fail, leave the findings file with no failure rows.
- [x] 4.7 Run `pytest tests/travel_engine -v` and confirm exit 0.

## 5. Cross-check

- [x] 5.1 Confirm the diff stays inside the paths in the proposal: `src/core/llm/client.py`, `src/config.py`, `.env.example`, `evals/replay/**`, `scripts/run_evals.py`, `tests/core/**`, `src/evaluation/metrics/**`, `tests/evaluation/**`, `tests/travel_engine/**`. No `requirements.txt` change, no `src/evaluation/scorers.py` change, no `src/travel_engine/**` change, no `.github/workflows/**` change, and no `docs/context.md` change.
- [x] 5.2 Run `pytest tests/architecture -k g1` and confirm the provider SDK is still imported only from `src/core/llm/client.py`. Put the blueprint §19 completion report in the PR description.
