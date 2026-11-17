## ADDED Requirements

### Requirement: ADR-006 records run tracking and idempotency scope
The repository SHALL contain an accepted decision record at `docs/v8.2/adr/006-run-tracking-idempotency.md` with context, decision, alternatives, consequences, migration and rollback, and status `accepted`. The record MUST state that the idempotency key is not the preference-cache key, that the preference-cache key is unchanged, that this slice adds no checkpoint, resume, lease, or worker, and that it adds no cancel route. Disconnect remains the way an in-flight generate stops. The record MUST state that `RUN_TRACKING_ENABLED` defaults to false.

#### Scenario: Record exists and is accepted
- **WHEN** subslice 1.2–1.4 is complete
- **THEN** `docs/v8.2/adr/006-run-tracking-idempotency.md` exists and its status is `accepted`

#### Scenario: Cache key stays separate
- **WHEN** the record states how a repeated submit is identified
- **THEN** it says the idempotency key is not the preference-cache key and the cache key is unchanged

#### Scenario: Cancel route and resume stay out
- **WHEN** the record states what this slice refuses
- **THEN** it says there is no cancel route, no checkpoint, and no resume, and that client disconnect still stops the in-flight generate

#### Scenario: Rollback is the flag
- **WHEN** the record states rollback
- **THEN** it says `RUN_TRACKING_ENABLED` defaults to false and turning it off restores generate without run writes
