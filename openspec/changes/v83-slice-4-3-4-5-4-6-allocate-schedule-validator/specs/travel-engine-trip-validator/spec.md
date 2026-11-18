## ADDED Requirements

### Requirement: V2 findings sit beside the v6.1 chain
`validate_trip` MUST keep the current chain, string `errors`, string `warnings`, and `passed` semantics, including `empty_itinerary` and the dropped-stops warning token. A separate pure collector MUST return `ValidationFinding` records for the same itinerary without changing that `ValidationResult`. The collector MUST NOT import geo, HTTP, SQLAlchemy, an LLM client, or `get_settings()`. It MUST accept optional plain search-area numbers and a geometry-promised flag from the caller. It MUST NOT import `SearchArea`.

#### Scenario: Legacy pass result is unchanged
- **WHEN** `validate_trip` runs on a fixture that passes today
- **THEN** `passed` is true, `errors` is empty, and the dropped-stops warning behavior is unchanged

#### Scenario: Findings do not rewrite string errors
- **WHEN** the findings collector reports a non-blocking code for an otherwise valid itinerary
- **THEN** `validate_trip` still returns `passed` true and does not add that code to `errors`

### Requirement: v6.1 predicates remain the source of the matching findings
The collector MUST emit `EXCESSIVE_TRAVEL_TIME` when `check_daily_travel_cap` would append an error, `DUPLICATE_STOP` when `check_no_repeat_places` would, `MORNING_ONLY_VIOLATION` when `check_morning_slots` would, `NO_ANCHOR_ATTRACTION` when `check_anchor_per_day` would, and `GEO_INCOHERENT_DAY` when `check_geo_coherence` would. Those findings MUST use the registry severity and `blocks_publish` values. Emitting them MUST NOT remove or reword the existing string errors.

#### Scenario: Over-cap day still has the string error and a finding
- **WHEN** a day's `total_travel_min` exceeds `MAX_DAILY_TRAVEL_MIN`
- **THEN** `errors` still identifies that day and findings include `EXCESSIVE_TRAVEL_TIME` with `blocks_publish` false
