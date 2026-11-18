## Purpose

Offline golden-dataset evaluation harness: property-based itinerary cases replayed through the real generation pipeline, scored by deterministic pure-Python scorers, with run reports and baseline diffing for regression gating.

## Requirements

### Requirement: Golden case schema is property-based
Golden cases SHALL be versioned JSON files grouped per destination, asserting properties of a generated itinerary (constraint satisfaction, must-include places, validation pass, readiness, fallback, and tool-call bounds). A case MUST NOT assert an exact output string or a place ordering. Each case MUST carry schema version `2`, a stable non-empty `id`, a non-empty `destination`, a non-empty `raw_input`, a `case_type` from the closed set below, a `labels` array, a boolean `quarantined` flag, and a non-empty `assertions` object whose keys are in the closed assertion set. `destination_id`, when present, MUST be a non-empty string. `must_include_places`, when present, MUST be an array of non-empty strings.

`schema_version` MUST be the integer `2`. Any other value, including the string `"2"`, MUST be rejected.

`case_type` MUST be one of: `landmark_vs_city`, `ambiguous_name`, `map_pin_radius`, `neighborhood_or_address`, `sparse_data`, `multi_day`, `duplicate_prone`, `routing_failure`, `llm_unavailable`, `over_travel_budget`, `unknown_opening_hours`, `guide_suggestion`, `itinerary_preference`. The twelve existing Darjeeling cases MUST be migrated in place to `itinerary_preference`. None of those files MUST be deleted, and none MUST be relabeled as a location, routing, or model-failure type.

`labels` MUST be an array of non-empty strings. An empty array is valid. A duplicate entry MUST be rejected.

`quarantined` MUST be a boolean. When it is `false`, `quarantine_owner` MUST be absent. When it is `true`, `quarantine_owner` MUST be a non-empty string. A quarantined case MUST remain in the loaded set with `quarantined` still true. This requirement does not remove it from scoring.

`assertions` MUST be a non-empty object using only these keys and types:

- `validation_passed`: boolean
- `max_days`: integer
- `min_places_per_day`: integer
- `readiness_score_min`: number
- `no_geo_fallback`: boolean
- `max_tool_calls`: integer

An unknown assertion key MUST be rejected. A value of the wrong type MUST be rejected, including a numeric value written as a string. A boolean assertion MUST be a JSON boolean, not `0` or `1`.

`id`, `destination`, and `raw_input` MUST be non-empty strings. A present `destination_id` that is empty or not a string MUST be rejected. A present `must_include_places` that is not an array of non-empty strings MUST be rejected. Those failures use the code `invalid_field`. An absent required key uses `missing_field`. `quarantine_owner` present while `quarantined` is false uses `invalid_quarantine`.

A case that fails these rules MUST be rejected before any case in that load is scored. The failure MUST name the offending file and exactly one of these codes: `invalid_json`, `not_an_object`, `missing_field`, `invalid_field`, `invalid_schema_version`, `invalid_case_type`, `invalid_labels`, `invalid_quarantine`, `missing_quarantine_owner`, `empty_assertions`, `unknown_assertion`, `invalid_assertion_value`. The load MUST NOT call an LLM, the network, or a database.

#### Scenario: Case file validates against schema
- **WHEN** the loader reads golden cases for a destination
- **THEN** every returned case has schema version `2`, an id, a destination, a raw input, a case type, labels, a quarantined flag, and at least one assertion, and a malformed case fails before scoring with that file's name and one error code

#### Scenario: Schema v2 case loads
- **WHEN** a destination folder contains one object with schema version `2`, a non-empty id, destination, and raw input, case type `itinerary_preference`, labels `["darjeeling"]`, `quarantined` false, no `quarantine_owner`, and assertions `{ "validation_passed": true }`
- **THEN** the load returns that case with those fields unchanged

#### Scenario: Existing Darjeeling cases still load
- **WHEN** the Darjeeling golden folder is loaded after the in-place migration
- **THEN** the load returns the same twelve case ids that existed before this change, each with schema version `2` and case type `itinerary_preference`

#### Scenario: Missing schema version fails by name
- **WHEN** a case file omits `schema_version`
- **THEN** the load fails before scoring, and the error names that file and the code `missing_field`

#### Scenario: Unknown case type fails by name
- **WHEN** a case file sets `case_type` to `city`
- **THEN** the load fails before scoring, and the error names that file and the code `invalid_case_type`

#### Scenario: Unknown assertion key fails by name
- **WHEN** a case file includes an assertion key `narrative_contains`
- **THEN** the load fails before scoring, and the error names that file and the code `unknown_assertion`

#### Scenario: String number fails by name
- **WHEN** a case file sets `max_days` to `"3"`
- **THEN** the load fails before scoring, and the error names that file and the code `invalid_assertion_value`

#### Scenario: Quarantined case without an owner fails
- **WHEN** a case file sets `quarantined` to true and omits `quarantine_owner`
- **THEN** the load fails before scoring, and the error names that file and the code `missing_quarantine_owner`

#### Scenario: Owner on a non-quarantined case fails
- **WHEN** a case file sets `quarantined` to false and sets `quarantine_owner` to a non-empty string
- **THEN** the load fails before scoring, and the error names that file and the code `invalid_quarantine`

#### Scenario: Quarantined case stays loaded
- **WHEN** a case file sets `quarantined` to true and `quarantine_owner` to a non-empty string, and the rest of the case is valid
- **THEN** the load returns that case with `quarantined` still true

### Requirement: Golden load does not change scoring or the gate
Loading a golden case MUST NOT change how a generation result is scored, MUST NOT change baseline file contents by itself, and MUST NOT drop a quarantined case from the loaded set. A quarantined flag is data for the regression gate. The loader MUST NOT skip the case. Gate exclusion of quarantined cases is owned by the regression gate, not by the loader.

#### Scenario: Quarantined case is still returned
- **WHEN** a destination folder contains one valid quarantined case and one valid non-quarantined case
- **THEN** the load returns both cases

#### Scenario: Scoring keys stay the existing set
- **WHEN** a valid case asserts `validation_passed`, `max_days`, `min_places_per_day`, `readiness_score_min`, `no_geo_fallback`, and `max_tool_calls`
- **THEN** the load accepts the case and does not add or remove assertion keys

### Requirement: Deterministic scorers are pure functions
Scorers SHALL be pure Python functions (no LLM, no network, no DB I/O) that take a generation result plus a case and return pass/fail with a reason. Route feasibility scoring MUST reuse the existing trip validator. Scoring MUST NOT mutate inputs.

#### Scenario: Feasibility scorer reuses trip validator
- **WHEN** a case asserts `validation_passed`
- **THEN** the scorer's verdict matches what the existing trip validator reports for the generated itinerary

#### Scenario: Scorers are deterministic
- **WHEN** the same result is scored twice
- **THEN** both runs return identical verdicts and reasons

### Requirement: Runner replays through the production pipeline
The runner SHALL execute each golden case through the same planner service entry point used in production, with routing injected via the test fake-routing pattern, and SHALL NOT require live external services beyond those already required by the dev stack (DB, Qdrant, optional LLM). Each run SHALL produce a machine-readable report (per-case verdicts, scores, timings, git SHA, timestamp) under `evals/runs/`.

#### Scenario: Full suite run produces report
- **WHEN** the runner executes all cases for a destination
- **THEN** a single JSON report exists listing every case id with verdict, individual assertion results, and aggregate pass rate

#### Scenario: LLM-unavailable mode still scores deterministic assertions
- **WHEN** no LLM key is configured and cases are replayed from recorded states or fallback paths
- **THEN** deterministic assertions (constraints, validator, fallback flags) are still evaluated and reported

### Requirement: Baseline diff gates regressions
The runner SHALL compare a new run against a designated baseline report and exit non-zero when any previously-passing **non-quarantined** case regresses to fail. Each such regression MUST be printed with the code `REGRESSION` and the case id. A `--update-baseline` mode SHALL freeze the current run as the new baseline explicitly. A run without that flag MUST NOT modify baseline files. Aggregate pass rate in the report MUST be computed over non-quarantined cases for the gate; quarantined outcomes MAY appear in a separate report section.

#### Scenario: Regression exits non-zero
- **WHEN** a non-quarantined case passed in the baseline but fails in the new run
- **THEN** the runner prints a `REGRESSION` line for that case and exits non-zero

#### Scenario: All-pass run exits zero
- **WHEN** every non-quarantined case passes identically to baseline
- **THEN** the runner exits zero

#### Scenario: Baseline update is explicit
- **WHEN** the runner is invoked with the update-baseline flag
- **THEN** the current run replaces the stored baseline and the command exits zero

#### Scenario: Quarantined regression is not a gate fail
- **WHEN** only a quarantined case moves from pass to fail and every non-quarantined case matches baseline
- **THEN** the runner exits zero

### Requirement: Replay runs the golden suite twice identically
`scripts/run_evals.py --replay` MUST force gateway replay for that process even when `LLM_REPLAY_MODE` is `off`. It MUST NOT read or write process environment variables. It MUST NOT call a provider. Two consecutive `--replay` runs of the same destination MUST produce the same per-case verdicts and the same reasons. A missing fixture MUST make that run exit non-zero and MUST print `replay_miss`. `--replay` MUST NOT change baseline files, MUST NOT change `--update-baseline` or `--fixtures-only`, and MUST NOT change schema validation or how a case passes or fails.

#### Scenario: Two replay runs match
- **WHEN** the Darjeeling suite is run with `--replay` twice and every gateway call has a fixture
- **THEN** the per-case verdicts and reasons are identical and the provider is not called

#### Scenario: Missing fixture fails the run
- **WHEN** `--replay` reaches a gateway call with no fixture
- **THEN** the process exits non-zero and the output contains `replay_miss`

#### Scenario: Replay leaves the baseline untouched
- **WHEN** `--replay` finishes
- **THEN** the stored baseline files are unchanged

### Requirement: The location suite does not enter the itinerary loader
`python scripts/run_evals.py --replay --suite location` MUST score only `evals/golden/location/*.json` and MUST exit 0 when those cases meet the location gates. It MUST NOT call `PlannerService`, an LLM, the network, or a database. `--replay` on that suite MUST NOT read provider fixtures and MUST NOT change the score.

The default command without `--suite` MUST keep loading `evals/golden/darjeeling` only. The twelve Darjeeling files MUST stay `itinerary_preference`. The closed itinerary assertion set MUST NOT gain keys for this suite. Location files MUST NOT be passed through that assertion loader.

The suite MUST report location-type accuracy of at least 0.95, MUST show that every ambiguous case asks for confirmation and does not select a candidate, and MUST show search-area containment of at least 0.98. A labeled stop outside the area MUST be excluded. The fixtures MUST cover a city (`Darjeeling`), a landmark (`Tiger Hill`), an ambiguous pair, a map pin whose radius clamps at `LOCATION_MAX_RADIUS_KM`, and one stop outside a radius.

#### Scenario: The location command does not generate a trip
- **WHEN** `python scripts/run_evals.py --replay --suite location` runs
- **THEN** it exits 0, does not call the planner, and does not score the Darjeeling itinerary files

#### Scenario: The default replay command ignores the location folder
- **WHEN** `python scripts/run_evals.py --replay` runs with no `--suite`
- **THEN** it loads the Darjeeling itinerary cases and does not load `evals/golden/location`

#### Scenario: An outside stop fails containment
- **WHEN** a location case marks a stop outside the area and the filter keeps that stop
- **THEN** the suite exits non-zero

### Requirement: The retrieval suite does not enter the itinerary loader

`python scripts/run_evals.py --replay --suite retrieval` MUST score only `evals/golden/retrieval/*.json`. It MUST call the existing recall-at-k function with k equal to 10. It MUST NOT change that function's formula. It MUST NOT call `PlannerService`, an LLM, Qdrant, the network, or a database. `--replay` on that suite MUST NOT read provider fixtures and MUST NOT change the recall score.

The default command without `--suite` MUST keep loading `evals/golden/darjeeling` only. Retrieval files MUST NOT be passed through the itinerary assertion loader. `score_case` verdicts and Darjeeling assertion keys MUST stay unchanged.

Each retrieval case MUST name an ordered retrieved-id list and a non-empty must-include id list. Recall for a case MUST be the existing metric on those lists at k 10. A case whose recall is below 0.80 MUST make the suite exit non-zero. The suite mean MUST be at least 0.80 and at least the mean stored in `evals/baselines/retrieval.json`. A mean below that baseline MUST exit non-zero and MUST print `retrieval_recall@10`. A run without `--update-baseline` MUST NOT write that baseline file. `--update-baseline` on this suite MUST replace that file with the current mean and MUST exit 0 only when every case is at least 0.80.

The checked-in suite MUST cover at least one case whose hand-computed recall is 1.0 and at least one case whose hand-computed recall is exactly 0.80, so the floor is exercised by a passing case rather than by an unused test double.

#### Scenario: The retrieval command does not generate a trip

- **WHEN** `python scripts/run_evals.py --replay --suite retrieval` runs on the checked-in cases
- **THEN** it exits 0, does not call the planner, and does not score the Darjeeling itinerary files

#### Scenario: The default replay command ignores the retrieval folder

- **WHEN** `python scripts/run_evals.py --replay` runs with no `--suite`
- **THEN** it loads the Darjeeling itinerary cases and does not load `evals/golden/retrieval`

#### Scenario: A case under 0.80 fails the suite

- **WHEN** a retrieval case has two must-include ids and only one of them is inside the first 10 retrieved ids
- **THEN** that case's recall is 0.5 and the suite exits non-zero

#### Scenario: A mean below the baseline fails the suite

- **WHEN** every case is at least 0.80 and the suite mean is lower than `evals/baselines/retrieval.json`
- **THEN** the process exits non-zero and the output contains `retrieval_recall@10`

#### Scenario: Darjeeling scoring is unchanged

- **WHEN** an existing Darjeeling case is scored by `score_case` before and after the retrieval suite runs
- **THEN** the pass or fail verdict and the reasons for that case stay the same
