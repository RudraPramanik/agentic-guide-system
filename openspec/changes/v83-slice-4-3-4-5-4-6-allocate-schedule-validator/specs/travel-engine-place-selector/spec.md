## ADDED Requirements

### Requirement: Place candidates carry optional hours fields
`PlaceCandidate` MUST accept optional `opening_hours_status` with values `verified`, `unknown`, and `malformed`, defaulting to `unknown`, plus optional naive `opening_open` and `opening_close` strings defaulting to null. Existing candidates that omit these fields MUST still validate. Scoring and `select_places` MUST ignore the hours fields. The module MUST NOT parse an OSM hours string and MUST NOT add a parser dependency.

#### Scenario: Omitted hours stay unknown
- **WHEN** a candidate is built with only the current required fields
- **THEN** `opening_hours_status` is `unknown` and the open and close strings are null

#### Scenario: Scoring ignores hours
- **WHEN** two candidates differ only by opening status and are scored with the same interests
- **THEN** their scores are equal
