## 1. Confirm scope

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, `docs/steps/wandr_blueprint_version8.md` §9 row 2.1 and §11.2, plus this change's `proposal.md`, `design.md`, and `specs/eval-golden-harness/spec.md`. There is no `docs/steps/step*.md` for this row.
- [x] 1.2 Confirm writes stay inside `src/evaluation/golden.py`, `evals/golden/**`, `tests/evaluation/test_golden_loader.py`, and the load call in `scripts/run_evals.py`. Do not edit `src/evaluation/scorers.py`, `src/core/llm/client.py`, `src/config.py`, `.github/workflows/**`, `tests/travel_engine/**`, or `docs/context.md`.

## 2. Loader

- [x] 2.1 Add `src/evaluation/golden.py` with `GoldenCaseError` (`code`, `filename`, message `{filename}: {code}`) and `load_golden_cases(folder) -> list[dict]`. Read `*.json` in sorted file-name order with `utf-8-sig`. Return the parsed objects. Keep unknown top-level keys. On the first failure, raise and return nothing.
- [x] 2.2 Implement the spec's closed `case_type` set, the six assertion keys and their types, and the code list. Reject `bool` for integer and number assertions. Reject schema version other than the integer `2`, including the string `"2"`. Use `missing_field` for an absent required key, `invalid_field` for a present id, destination, raw input, `destination_id`, or `must_include_places` of the wrong shape, and `invalid_quarantine` when `quarantine_owner` is present while `quarantined` is false.

## 3. Migrate the Darjeeling cases

- [x] 3.1 Add `schema_version` 2, `case_type` `itinerary_preference`, `labels` `["darjeeling"]`, and `quarantined` false to each of the twelve files `dar-001.json` through `dar-012.json`. Do not add `quarantine_owner`. Do not change `id`, `destination`, `destination_id`, `raw_input`, `must_include_places`, or `assertions`. Do not delete a file.
- [x] 3.2 Update `evals/golden/darjeeling/README.md` so the required fields, the case-type set, and the assertion keys match the spec.

## 4. Wire the runner

- [x] 4.1 In `scripts/run_evals.py`, replace the inline field checks inside `_load_cases` with `load_golden_cases`. Turn `GoldenCaseError` into `SystemExit` using the exception message. Keep the current `SystemExit` text for a missing destination folder and for a folder with no JSON files.
- [x] 4.2 Leave generate, `--fixtures-only`, `--update-baseline`, and baseline diff behavior unchanged. Do not drop a quarantined case from the returned list.

## 5. Tests

- [x] 5.1 Add `tests/evaluation/test_golden_loader.py` for the spec scenarios: a valid v2 case, missing `schema_version` (`missing_field`), case type `city` (`invalid_case_type`), assertion `narrative_contains` (`unknown_assertion`), `max_days` `"3"` (`invalid_assertion_value`), quarantined without an owner (`missing_quarantine_owner`), owner present while `quarantined` is false (`invalid_quarantine`), and a folder that returns both a quarantined case and a non-quarantined case.
- [x] 5.2 Add a test that loads `evals/golden/darjeeling` and returns `dar-001` through `dar-012`, each with schema version `2` and case type `itinerary_preference`.
- [x] 5.3 Add a test that a case whose assertions use all six existing keys loads and comes back with those same keys.

## 6. Verify

- [x] 6.1 Run `pytest tests/evaluation -v` and confirm exit 0.
- [x] 6.2 Confirm the diff is only the paths in task 1.2. No `requirements.txt` edit, no setting, no HTTP route, and no edit to `docs/context.md`. Put the blueprint §19 completion report in the PR description.
