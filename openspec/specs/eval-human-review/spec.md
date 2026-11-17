# eval-human-review Specification

## Purpose

Versioned human-review sheet format under `evals/human_review/` that uses the same preference and quality dimensions as the offline judge so calibration can compare humans and the judge.

## Requirements

### Requirement: Human-review sheet is versioned and dimension-aligned
The repository MUST include a human-review sheet format under `evals/human_review/` with a rubric version identifier. The sheet MUST list the same pass/fail dimensions the offline judge uses, plus a free-text field per trip. A sheet instance MUST record destination, case or trip id, reviewer id, and the rubric version. The format MUST NOT require a live LLM call to validate.

#### Scenario: Sheet validates without an LLM
- **WHEN** a review sheet file includes rubric version, shared dimensions, reviewer id, and free-text
- **THEN** validation accepts it without calling the gateway

#### Scenario: Missing rubric version fails validation
- **WHEN** a review sheet omits the rubric version
- **THEN** validation rejects that sheet

### Requirement: Rubric dimensions match the judge
The human-review rubric dimensions MUST be the same closed set as the offline judge dimensions for preference and quality. Adding a dimension to one without the other MUST be rejected by the shared dimension list used by both formats.

#### Scenario: Shared dimensions stay aligned
- **WHEN** the judge rubric lists relevance, diversity, and narrative
- **THEN** the human-review sheet format requires those same three dimensions and no silent rename
