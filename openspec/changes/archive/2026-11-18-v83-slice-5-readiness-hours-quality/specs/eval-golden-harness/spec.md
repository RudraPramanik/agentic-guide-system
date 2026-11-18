## ADDED Requirements

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
