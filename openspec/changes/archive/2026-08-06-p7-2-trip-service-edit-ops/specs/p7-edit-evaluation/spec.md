## MODIFIED Requirements

### Requirement: mark_trip_edited is flag-only

The system SHALL provide `EvaluationService.mark_trip_edited(trip_id)` that looks up the latest `TripEvaluation` for the trip (if any) and sets `user_edited=True` via a flush-only repository helper. A thin no-op-safe implementation is acceptable for step 7.2 as long as the method exists, never raises on missing evaluation, and never touches `TripEditEvent`. It MUST NOT create, update, or delete `TripEditEvent` rows. Missing evaluation MUST be a no-op (edit still succeeds). TripService MUST call `mark_trip_edited` in the same UoW after inserting the `TripEditEvent` and before commit. Full evaluation-lookup polish MAY land in step 7.5 without changing this call site.

#### Scenario: Edit with existing evaluation sets flag

- **WHEN** a successful P7 edit runs for a trip that has a TripEvaluation and `mark_trip_edited` performs a real lookup
- **THEN** that evaluation’s `user_edited` is True after commit

#### Scenario: Edit without evaluation still audits

- **WHEN** a successful P7 edit runs for a trip with no TripEvaluation
- **THEN** a `TripEditEvent` exists after commit and `mark_trip_edited` does not raise

#### Scenario: mark_trip_edited never inserts edit events

- **WHEN** `mark_trip_edited` is invoked
- **THEN** it performs zero inserts into `trip_edit_events`
