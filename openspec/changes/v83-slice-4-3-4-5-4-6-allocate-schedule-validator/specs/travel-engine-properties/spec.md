## MODIFIED Requirements

### Requirement: Flag equivalence is the single current engine
Travel-engine source MUST NOT call `get_settings()` and MUST NOT contain the setting names `TRAVEL_ENGINE_V2_ENABLED` or `VALIDATOR_V2_ENFORCE`. V2 behavior MUST be selected only via an injected pure parameter from the planner tool boundary. With that parameter off, `select_places` (and scoring) MUST match the v6.1 sum-of-matching-weights path for the same inputs, `allocate_days` MUST match the current packing, and `build_day_schedule` MUST match the current timing. The settings themselves MAY exist on `Settings` for tools to read. Allocator, schedule, and validator MAY expose an injected mode; they MUST NOT read settings to choose it.

#### Scenario: Engine does not branch on a V2 flag
- **WHEN** the travel-engine sources are scanned
- **THEN** none of them contain `TRAVEL_ENGINE_V2_ENABLED` or `VALIDATOR_V2_ENFORCE`, and none call `get_settings`

## ADDED Requirements

### Requirement: Default allocator and schedule stay the property subject
Property checks for caps, chronology, and coherence MUST keep calling the default (mode-off) allocator and schedule. A V2 mode-on result MUST be covered by its own feature tests and MUST NOT be required to replace those default-path properties.

#### Scenario: Cap property still uses the default allocator
- **WHEN** the budget property runs
- **THEN** it calls `allocate_days` without V2 mode and still expects each day to honor the active-time cap and the place cap
