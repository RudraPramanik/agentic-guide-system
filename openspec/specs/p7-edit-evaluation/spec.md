## Purpose

P7 evaluation linkage on trip edits — `mark_trip_edited` flag-only (v2.1). TripService owns `TripEditEvent` creation.

## Requirements

### Requirement: mark_trip_edited is flag-only

The system SHALL provide `EvaluationService.mark_trip_edited(trip_id)` that looks up the latest `TripEvaluation` for the trip via `EvaluationRepository.get_latest_for_trip(trip_id)` and, when a row exists and `user_edited` is False, sets `user_edited=True` via flush-only `EvaluationRepository.mark_user_edited(evaluation)`. When no evaluation exists, or the latest row is already `user_edited=True`, the method MUST be a no-op (MUST NOT raise). It MUST NOT create, update, or delete `TripEditEvent` rows. It MUST NOT call LLM, planner, or travel_engine. TripService MUST call `mark_trip_edited` in the same UoW after inserting the `TripEditEvent` and before commit. No new `TripEvaluation` columns, migrations, or evaluation HTTP routes are introduced by this requirement.

#### Scenario: Edit with existing evaluation sets flag

- **WHEN** a successful P7 edit runs for a trip that has a `TripEvaluation` with `user_edited=False`
- **THEN** that evaluation’s `user_edited` is True after commit

#### Scenario: Edit without evaluation still audits

- **WHEN** a successful P7 edit runs for a trip with no `TripEvaluation`
- **THEN** a `TripEditEvent` exists after commit, the edit succeeds, and `mark_trip_edited` does not raise

#### Scenario: mark_trip_edited never inserts edit events

- **WHEN** `mark_trip_edited` is invoked (with or without an evaluation row)
- **THEN** it performs zero inserts into `trip_edit_events`

#### Scenario: Already-edited evaluation is left unchanged

- **WHEN** `mark_trip_edited` runs and the latest evaluation already has `user_edited=True`
- **THEN** the method returns without error and does not require a further mutation

### Requirement: Evaluation rows record real token usage
The evaluation write path SHALL persist actual cumulative token usage (prompt/completion/total) and LLM retry count observed during a generation into the existing `TripEvaluation` columns. When no LLM calls occurred, `token_usage` SHALL be written as an empty/zero value rather than remaining never-populated.

#### Scenario: Token usage populated after generation with LLM calls
- **WHEN** a generation completes that made one or more LLM gateway calls
- **THEN** the latest `TripEvaluation` row for the run has non-empty `token_usage` totals matching the sum of captured per-call usage

#### Scenario: Retry count reflects gateway retries
- **WHEN** the LLM gateway performed retries before success or exhaustion during a generation
- **THEN** the written `llm_retry_count` is greater than zero and equals the number of retry attempts observed
