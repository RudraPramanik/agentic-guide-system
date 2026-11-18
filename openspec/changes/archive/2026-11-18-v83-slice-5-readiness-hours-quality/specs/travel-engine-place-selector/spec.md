## ADDED Requirements

### Requirement: PlaceCandidate preserves raw hours and does not parse them

`PlaceCandidate` MUST accept an optional `opening_hours_raw` string defaulting to null. Existing candidate dicts that omit the field MUST still validate. Scoring and selection MUST ignore `opening_hours_raw`, `opening_hours_status`, `opening_open`, and `opening_close`. The selector module MUST NOT parse an OSM hours string and MUST NOT add a parser dependency. The travel engine MUST NOT read `READINESS_V2_ENABLED`.

#### Scenario: Legacy candidate dict still validates without raw hours

- **WHEN** a dict with only `id`, `name`, `category`, `enriched_tags`, `lat`, and `lng` is validated as `PlaceCandidate`
- **THEN** validation succeeds and `opening_hours_raw` is null

#### Scenario: Hours fields do not change the score

- **WHEN** two candidates differ only in `opening_hours_raw` and `opening_hours_status`
- **THEN** their scores are equal
