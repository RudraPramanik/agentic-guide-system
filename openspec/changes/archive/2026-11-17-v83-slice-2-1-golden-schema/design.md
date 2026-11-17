## Context

See proposal.md for why this subslice exists. The behavior contract is `specs/eval-golden-harness/spec.md`.

The loader today is the private `_load_cases` function in `scripts/run_evals.py`. It checks that a file is a JSON object with `id`, `destination`, `raw_input`, and a non-empty `assertions` object, then returns the dict. `src/evaluation/scorers.py` reads `must_include_places` plus the six assertion keys and ignores any other assertion key. The twelve Darjeeling files under `evals/golden/darjeeling/` are the only golden cases. There is no external call in this subslice, so no timeout, retry, or fallback is added. `travel_engine/` is not touched.

## Goals / Non-Goals

**Goals:**

- One pure loader that rejects a bad file with one code and the file name, and that the eval script calls.
- An in-place migration that leaves every current case id and every current assertion value in place.
- Tests that fail if a Darjeeling file is deleted or relabeled.

**Non-Goals:**

- A second validation pass inside `score_case`. The scorer keeps treating assertion keys as optional.
- Skipping quarantined cases, rewriting baselines, or changing the runner's generate and fixture paths.

## Decisions

### 1. The loader lives in `src/evaluation/golden.py` and returns dicts

`load_golden_cases(folder: Path) -> list[dict]` reads `*.json` in sorted file-name order, using `utf-8-sig` as the current script does. It returns the parsed objects, not a new model, so `score_case` still receives a dict.

`GoldenCaseError` carries `code` and `filename`. The message is `{filename}: {code}`. The first failing file aborts the load. Later files are not scored because the caller never receives a list.

Unknown top-level keys are kept. The schema does not forbid them, and dropping them would change fields the runner already passes through, such as `destination_id`.

Alternative considered: a Pydantic model. Rejected because the project would then translate Pydantic's default errors into the closed code list, and this subslice adds no package and no new pattern in `src/evaluation/`.

### 2. Type checks treat booleans as neither integers nor numbers

JSON `true` is a Python `bool`, and `bool` is a subclass of `int`. An assertion that must be an integer or a number rejects `bool`. A boolean assertion accepts only `bool`. A number written as a string is `invalid_assertion_value`. Schema version accepts only the integer `2`.

`invalid_field` covers a present `id`, `destination`, `raw_input`, `destination_id`, or `must_include_places` whose type or emptiness is wrong. `missing_field` covers an absent required key, including an absent `schema_version`.

### 3. Migrated Darjeeling files gain four keys and nothing else

Each of the twelve files gains:

- `"schema_version": 2`
- `"case_type": "itinerary_preference"`
- `"labels": ["darjeeling"]`
- `"quarantined": false`

`id`, `destination`, `destination_id`, `raw_input`, `must_include_places`, and `assertions` stay as they are. No `quarantine_owner`. The label is the destination the file already names. A theme parsed out of `raw_input` would be a new claim.

`evals/golden/darjeeling/README.md` lists the new required fields and the closed case-type and assertion sets. It is not loaded.

Alternative considered: leave `labels` as `[]`. Rejected because the destination string is already on the file and an explicit label is what later slices will group on. The array is still allowed to be empty for a new file.

### 4. The script replaces its inline checks and keeps its own folder errors

`scripts/run_evals.py` calls `load_golden_cases` and turns `GoldenCaseError` into `SystemExit` with the same `{filename}: {code}` message. A missing destination folder and a folder with no JSON files keep the script's current `SystemExit` text. Those are not case-file errors, and the spec does not assign them a code.

The script does not grow a replay flag, a baseline change, or a generate change. `--update-baseline` and `--fixtures-only` stay as they are.

## Risks / Trade-offs

- [A hand-edited golden file uses a string for `schema_version` or `max_days`] → The loader rejects it with `invalid_schema_version` or `invalid_assertion_value` before a run. The README states the types.
- [A later change treats `quarantined: true` as a skip] → This subslice's test loads a quarantined case and a normal case and expects both back. Gate exclusion stays in subslice 2.5.
- [The script keeps a private copy of the checks] → The inline checks are deleted, so a bad file has one implementation.
- [Windows BOM on an existing file] → The loader keeps `utf-8-sig`, which the current script already uses.

## Migration Plan

1. Add the loader and the tests.
2. Add the four keys to each Darjeeling case. Do not delete a file.
3. Point `scripts/run_evals.py` at the loader.
4. Rollback is reverting the change. There is no flag and no database revision. The old loader accepted files without the new keys, so a revert restores that behavior together with the old files.

## Open Questions

None. The case-type vocabulary, the assertion set, and the Darjeeling label are fixed by the spec.
