## Context

See proposal.md for why these three rows are one change. The behavior contracts are the delta specs under `specs/`.

`chat_completion`, `chat_with_tools`, and `embed_texts` in `src/core/llm/client.py` each call LiteLLM after the existing tenacity retry. The module already uses a `ContextVar` for retry counts. `scripts/run_evals.py` loads golden cases, calls the planner, and scores with `score_case`. It has `--fixtures-only`, `--update-baseline`, and `--allow-new-fails`, and no `--replay`. `src/evaluation/scorers.py` is the verdict function. `trip_validator._day_coord_stddev_km` is the dispersion formula (local-km offsets, sample variance, square root of the sum) and it is private. There is no `candidate_normalizer`, no `SearchArea`, and no `TRAVEL_ENGINE_V2_ENABLED`. `hypothesis` is not installed.

## Goals / Non-Goals

**Goals:**

- One replay identity, used by all three gateway functions, before any metric or property test is added.
- One coherence function, defined in 2.3 and called by the 2.4 property.
- A property suite that exits 0 without editing `src/travel_engine/`.

**Non-Goals:**

- A second coherence formula, a second fixture key, or a task that starts 2.4 before 2.3 exists.
- Wiring the eight metrics into `score_case` or into the baseline diff.

## Decisions

### 1. Apply order is 2.2, then 2.3, then 2.4

Tasks are grouped in that order. A later group does not start until the earlier group's tests pass. 2.3 does not import the gateway. 2.4 imports `geographic_coherence_km` and does not copy the formula. 2.2 does not import `src/evaluation`.

Alternative considered: three OpenSpec changes. Rejected because the user asked for one change that stays in order. The blueprint's one-PR-per-subslice rule is overridden for this batch only.

### 2. The mode is a setting plus a process-local override

`Settings.LLM_REPLAY_MODE` is a `str`, default `"off"`. A field validator rejects any value other than `off`, `replay`, and `record` at load. G11's flag table lists booleans from §7.1 and does not list this name, so `tests/architecture/_helpers.py` stays unchanged. A gateway test asserts the default is `off`.

`client.py` gains a `ContextVar` and `use_llm_replay(mode)`, following the existing `_retry_bumps` pattern. The effective mode is the context value when set, otherwise the setting. `scripts/run_evals.py --replay` calls `use_llm_replay("replay")` for the process and does not touch `os.environ`. When the flag is absent, the script leaves the context unset, so the setting applies. `--replay` wins over a setting of `off` or `record` for that process, and it does not write fixtures.

`.env.example` sets `LLM_REPLAY_MODE=off` next to the existing `LLM_*` lines.

Alternative considered: two booleans. Rejected because record and replay must not both be active.

### 3. The hook sits in the three public functions, before LiteLLM

For each of `chat_completion`, `chat_with_tools`, and `embed_texts`, the effective mode is checked in the public function:

- `replay`: load the fixture, return the existing result type, do not enter the retried inner function. Planner nodes catch `WandrLLMError`, so a miss is also appended to a context list inside `use_llm_replay`. `scripts/run_evals.py` prints `replay_miss` from that list when generate returns instead of raising.
- `record`: call the existing inner function (same timeout, same tenacity policy), then write the fixture, then return that result.
- `off`: today's path, unchanged.

`embed_texts` still returns `list[list[float]]`. A tool fixture still becomes `LLMToolResponse` with `{name, arguments_json}` tool calls. A miss raises `WandrLLMError(code="replay_miss")` and includes the fixture id. Empty content is not a stand-in for a miss.

The fixture id is the hex SHA-256 of canonical JSON: `operation`, `model`, and the payload (`messages` plus `response_format`, or `messages` plus `tools` and `tool_choice`, or `texts`). `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. The file is `evals/replay/<id>.json`. The file stores the result fields and the operation. It does not store the API key. Timestamps and retry bookkeeping are not part of the id. A tool-trace duration (`ms=<number>`) inside a message is replaced with `ms=0` before the hash, so a later call with the same logical trace keeps the same fixture. Replay returns the stored `retry_count` and does not sleep.

Alternative considered: hashing the raw message text only. Rejected because tool calls and embeddings would collide or miss.

### 4. Fixtures are recorded once, then replayed

During apply, if `LLM_API_KEY` is non-empty, one `record` run of the Darjeeling suite writes `evals/replay/**`, and those files are part of the change. The two `--replay` runs then call no provider. If the key is empty, stop and report that. Do not invent fixture bodies. A partial directory is not a success.

Unit tests do not need that live run. They write a temp fixture, or point the replay root at a temp directory, and assert identity, `replay_miss`, and that a mocked provider is not called.

### 5. Metrics are new functions and `score_case` stays

`src/evaluation/metrics/__init__.py` exports:

- `location_type_accuracy(predicted, labeled) -> float`
- `retrieval_recall_at_k(retrieved, labeled, k) -> float`
- `duplicate_stop_count(place_ids) -> int`
- `geographic_coherence_km(coords) -> float | None`
- `schedule_feasibility(days, active_cap, travel_cap) -> float` where each day is `(visit_min, travel_min)`
- `preference_match(places, interests) -> float` where each place is `(category, tags)`
- `persistence_match(generated, saved) -> bool` where each side is a list of id lists
- `map_itinerary_match(feature_ids, stop_ids) -> bool`

Empty labeled or empty selected inputs follow the spec (`1.0`, and unique ids yield duplicate count `0`). `geographic_coherence_km` copies the documented validator formula with the constant `111.0` and sample variance over `n - 1`. It does not import `trip_validator`, because that module is outside this row. Fewer than two points returns `None`.

`src/evaluation/scorers.py` is not edited. The path cell allows it. Editing it is how a verdict would drift, and 2.5 is the slice that may call these metrics from the gate.

Tests in `tests/evaluation/test_metrics.py` use the spec's hand-computed cases, including two identical coordinates scoring `0` and the farther-point case scoring strictly higher.

### 6. Property tests call the engine and the one metric

`tests/travel_engine/test_properties.py` covers the suite. `tests/travel_engine/PROPERTY_FINDINGS.md` starts with no failure rows.

- Determinism and order invariance call `select_places` and `allocate_days` on a fixed fixture. The shuffle test compares the selected set and day membership, not input order.
- Removal builds a `TripItinerary` with unique ids and increasing `suggested_start_time` values, drops one stop in the test, and checks ids and times. No new engine function.
- Monotonic coherence takes an allocated day's coordinates, appends a point farther from that centroid than either existing point, and asserts `geographic_coherence_km` does not decrease. The import is `src.evaluation.metrics.geographic_coherence_km`.
- Budget uses `ACTIVE_DAY_VISIT_BUDGET_MIN` and `MAX_PLACES_PER_DAY` from `travel_rules` on allocator output.
- Schedule uses `schedule_builder` output. Start times must be strictly increasing. A scheduled duration must equal the matching `RouteLeg` duration. Routing input is `FakeRoutingProvider` from `tests/travel_engine/fake_routing.py`.
- Flag equivalence scans `src/travel_engine/**/*.py` and fails if the text `TRAVEL_ENGINE_V2_ENABLED` appears. The setting is not added.
- Idempotent dedup is `pytest.mark.skip` with reason `slice 4.1 owns candidate normalizer`. Area respect is `pytest.mark.skip` with reason `slice 3 owns SearchArea`.

If a live property fails, add one row to `PROPERTY_FINDINGS.md` and mark that test `pytest.mark.xfail(reason="finding: <property>", strict=True)`. Do not edit `src/travel_engine/`. `strict=True` means a later slice that makes the property pass must remove the xfail in that slice, not here.

`hypothesis` is not added. The blueprint allows it only with a requirements comment, and seeded fixtures are enough.

### 7. Resilience

Mode `off` and `record` keep `LLM_TIMEOUT_SECONDS` and the existing tenacity retry for `Timeout` and `RateLimitError`. The named failure after retries stays `WandrLLMError` / `llm_unavailable`. `replay` does not call the provider, so it adds no timeout and no retry sleep. The named fallback for a missing fixture is `replay_miss`. Record writes the fixture only after the provider call returns. A failed provider call writes nothing.

## Risks / Trade-offs

- [A Darjeeling generate calls the gateway in an order that depends on live text] → Record once, then both replays serve those bytes, so the second run matches the first. A later prompt change invalidates ids and `--replay` fails with `replay_miss` until a reviewed re-record.
- [No API key in the apply environment] → Stop. Do not commit invented completions. Unit tests still cover the hook.
- [`--replay` still needs the dev database and Qdrant because the runner calls the planner] → That is the current runner. This change does not add a second runner. `--fixtures-only` stays for the path that never calls the planner.
- [The copied dispersion formula drifts from `_day_coord_stddev_km`] → The metric test's identical-point case is `0`, and the property test imports the metric only. A comment in the metric cites the validator function as the definition source. This slice does not export the private helper, because that would edit `trip_validator.py`.
- [An xfail hides an engine bug] → The finding file names it. Row 2.4 forbids a fix in this change.
- [Replay mode left on in a deployed env] → Default is `off`, `.env.example` says `off`, and a miss fails closed instead of calling the provider with an empty body.

## Migration Plan

1. Land the setting, the gateway hook, and the gateway tests.
2. Record Darjeeling fixtures if a key is present, then run `--replay` twice.
3. Land the metrics and their hand-computed tests. Do not edit `scorers.py`.
4. Land the property tests. Record findings instead of editing the engine.
5. Rollback is `LLM_REPLAY_MODE=off` plus reverting the change. There is no database revision. Mode `off` is today's gateway behavior.

## Open Questions

None. The mode name, the fixture identity, the coherence function, the skip reasons, and the apply order are fixed by the specs.
