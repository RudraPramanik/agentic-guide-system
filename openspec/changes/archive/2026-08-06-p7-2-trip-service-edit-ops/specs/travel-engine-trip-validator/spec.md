## ADDED Requirements

### Requirement: Morning-slot errors use stable prefix for edit downgrade

`check_morning_slots` error strings MUST begin with the exact prefix `morning_slot_violation: ` (including trailing space) before the existing human-readable day/place context. Message semantics (which stops fail) MUST remain unchanged. Other validator rules MUST NOT adopt this prefix. The change MUST remain pure (no I/O) and MUST NOT alter `passed` semantics — TripService MAY filter these strings on REORDER only.

#### Scenario: Late morning-only stop error is prefixed

- **WHEN** a morning-only place is scheduled after slot 2 (or starts after `MORNING_SLOT_LATEST_START`)
- **THEN** `errors` contains a string starting with `morning_slot_violation: ` that still identifies day and place

#### Scenario: Non-morning rules stay unprefixed

- **WHEN** only a daily travel-cap violation is present
- **THEN** that error does not start with `morning_slot_violation:`
