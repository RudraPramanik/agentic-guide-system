## ADDED Requirements

### Requirement: EvaluationService record_edit

The system SHALL implement `EvaluationService.record_edit(trip_id, edit_type, *, day_number=None, place_id=None, payload=None)` (or equivalent signature locked in `docs/steps/step7.md`) that:

- Ensures a `TripEditEvent` is persisted for the edit (flush-only; caller UoW commits), OR accepts an already-flushed event and only updates evaluation — step7 MUST pick one pattern and keep router/service consistent.
- Sets `user_edited=True` on the latest `TripEvaluation` row for that `trip_id` when one exists.
- When no evaluation row exists, MUST still allow the edit to succeed (audit event only; no hard failure).
- MUST NOT call LLM or planner services.
- On DB failure during flag update: log warning; MUST NOT convert a successful itinerary mutation into an uncaught 500 after commit policy — prefer including evaluation update inside the same UoW before commit so rollback covers both.

#### Scenario: Edit flags evaluation when present

- **WHEN** `record_edit` runs for a trip that has a `TripEvaluation` row
- **THEN** that evaluation’s `user_edited` is True after commit

#### Scenario: Edit without evaluation still audits

- **WHEN** `record_edit` runs for a trip with no `TripEvaluation`
- **THEN** a `TripEditEvent` is still recorded and the edit transaction can succeed

### Requirement: AGENT evaluation rule honored on edits

Edits MUST invoke the evaluation recording path so that every user-initiated edit is reflected in `trip_edit_events` (and `user_edited` when applicable), matching AGENT.md “evaluation records every generation and every edit.”

#### Scenario: All four edit types covered

- **WHEN** reorder, remove, add, and reoptimize each succeed once
- **THEN** four `TripEditEvent` rows exist with the four distinct `EditType` values
