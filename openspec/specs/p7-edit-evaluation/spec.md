## Purpose

P7 evaluation linkage on trip edits — `mark_trip_edited` flag-only (v2.1). TripService owns `TripEditEvent` creation.

## Requirements

### Requirement: mark_trip_edited is flag-only

The system SHALL provide `EvaluationService.mark_trip_edited(trip_id)` that looks up the latest `TripEvaluation` for the trip (if any) and sets `user_edited=True` via a flush-only repository helper. It MUST NOT create, update, or delete `TripEditEvent` rows. Missing evaluation MUST be a no-op (edit still succeeds). TripService MUST call `mark_trip_edited` in the same UoW after inserting the `TripEditEvent` and before commit.

#### Scenario: Edit with existing evaluation sets flag

- **WHEN** a successful P7 edit runs for a trip that has a TripEvaluation
- **THEN** that evaluation’s `user_edited` is True after commit

#### Scenario: Edit without evaluation still audits

- **WHEN** a successful P7 edit runs for a trip with no TripEvaluation
- **THEN** a `TripEditEvent` exists, HTTP is success, and `mark_trip_edited` does not raise

#### Scenario: mark_trip_edited never inserts edit events

- **WHEN** `mark_trip_edited` is invoked
- **THEN** it performs zero inserts into `trip_edit_events`
