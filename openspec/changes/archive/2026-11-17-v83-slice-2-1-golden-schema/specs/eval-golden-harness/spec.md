## MODIFIED Requirements

### Requirement: Golden case schema is property-based
Golden cases SHALL be versioned JSON files grouped per destination, asserting properties of a generated itinerary (constraint satisfaction, must-include places, validation pass, readiness, fallback, and tool-call bounds). A case MUST NOT assert an exact output string or a place ordering. Each case MUST carry schema version `2`, a stable non-empty `id`, a non-empty `destination`, a non-empty `raw_input`, a `case_type` from the closed set below, a `labels` array, a boolean `quarantined` flag, and a non-empty `assertions` object whose keys are in the closed assertion set. `destination_id`, when present, MUST be a non-empty string. `must_include_places`, when present, MUST be an array of non-empty strings.

`schema_version` MUST be the integer `2`. Any other value, including the string `"2"`, MUST be rejected.

`case_type` MUST be one of: `landmark_vs_city`, `ambiguous_name`, `map_pin_radius`, `neighborhood_or_address`, `sparse_data`, `multi_day`, `duplicate_prone`, `routing_failure`, `llm_unavailable`, `over_travel_budget`, `unknown_opening_hours`, `guide_suggestion`, `itinerary_preference`. The twelve existing Darjeeling cases MUST be migrated in place to `itinerary_preference`. None of those files MUST be deleted, and none MUST be relabeled as a location, routing, or model-failure type.

`labels` MUST be an array of non-empty strings. An empty array is valid. A duplicate entry MUST be rejected.

`quarantined` MUST be a boolean. When it is `false`, `quarantine_owner` MUST be absent. When it is `true`, `quarantine_owner` MUST be a non-empty string. A quarantined case MUST remain in the loaded set with `quarantined` still true. This requirement does not remove it from scoring.

`assertions` MUST be a non-empty object using only these keys and types:

- `validation_passed`: boolean
- `max_days`: integer
- `min_places_per_day`: integer
- `readiness_score_min`: number
- `no_geo_fallback`: boolean
- `max_tool_calls`: integer

An unknown assertion key MUST be rejected. A value of the wrong type MUST be rejected, including a numeric value written as a string. A boolean assertion MUST be a JSON boolean, not `0` or `1`.

`id`, `destination`, and `raw_input` MUST be non-empty strings. A present `destination_id` that is empty or not a string MUST be rejected. A present `must_include_places` that is not an array of non-empty strings MUST be rejected. Those failures use the code `invalid_field`. An absent required key uses `missing_field`. `quarantine_owner` present while `quarantined` is false uses `invalid_quarantine`.

A case that fails these rules MUST be rejected before any case in that load is scored. The failure MUST name the offending file and exactly one of these codes: `invalid_json`, `not_an_object`, `missing_field`, `invalid_field`, `invalid_schema_version`, `invalid_case_type`, `invalid_labels`, `invalid_quarantine`, `missing_quarantine_owner`, `empty_assertions`, `unknown_assertion`, `invalid_assertion_value`. The load MUST NOT call an LLM, the network, or a database.

#### Scenario: Case file validates against schema
- **WHEN** the loader reads golden cases for a destination
- **THEN** every returned case has schema version `2`, an id, a destination, a raw input, a case type, labels, a quarantined flag, and at least one assertion, and a malformed case fails before scoring with that file's name and one error code

#### Scenario: Schema v2 case loads
- **WHEN** a destination folder contains one object with schema version `2`, a non-empty id, destination, and raw input, case type `itinerary_preference`, labels `["darjeeling"]`, `quarantined` false, no `quarantine_owner`, and assertions `{ "validation_passed": true }`
- **THEN** the load returns that case with those fields unchanged

#### Scenario: Existing Darjeeling cases still load
- **WHEN** the Darjeeling golden folder is loaded after the in-place migration
- **THEN** the load returns the same twelve case ids that existed before this change, each with schema version `2` and case type `itinerary_preference`

#### Scenario: Missing schema version fails by name
- **WHEN** a case file omits `schema_version`
- **THEN** the load fails before scoring, and the error names that file and the code `missing_field`

#### Scenario: Unknown case type fails by name
- **WHEN** a case file sets `case_type` to `city`
- **THEN** the load fails before scoring, and the error names that file and the code `invalid_case_type`

#### Scenario: Unknown assertion key fails by name
- **WHEN** a case file includes an assertion key `narrative_contains`
- **THEN** the load fails before scoring, and the error names that file and the code `unknown_assertion`

#### Scenario: String number fails by name
- **WHEN** a case file sets `max_days` to `"3"`
- **THEN** the load fails before scoring, and the error names that file and the code `invalid_assertion_value`

#### Scenario: Quarantined case without an owner fails
- **WHEN** a case file sets `quarantined` to true and omits `quarantine_owner`
- **THEN** the load fails before scoring, and the error names that file and the code `missing_quarantine_owner`

#### Scenario: Owner on a non-quarantined case fails
- **WHEN** a case file sets `quarantined` to false and sets `quarantine_owner` to a non-empty string
- **THEN** the load fails before scoring, and the error names that file and the code `invalid_quarantine`

#### Scenario: Quarantined case stays loaded
- **WHEN** a case file sets `quarantined` to true and `quarantine_owner` to a non-empty string, and the rest of the case is valid
- **THEN** the load returns that case with `quarantined` still true

## ADDED Requirements

### Requirement: Golden load does not change scoring or the gate
Loading a golden case MUST NOT change how a generation result is scored, MUST NOT change baseline diffing, and MUST NOT drop a quarantined case from the loaded set. A quarantined flag is data for a later gate. It is not a skip.

#### Scenario: Quarantined case is still returned
- **WHEN** a destination folder contains one valid quarantined case and one valid non-quarantined case
- **THEN** the load returns both cases

#### Scenario: Scoring keys stay the existing set
- **WHEN** a valid case asserts `validation_passed`, `max_days`, `min_places_per_day`, `readiness_score_min`, `no_geo_fallback`, and `max_tool_calls`
- **THEN** the load accepts the case and does not add or remove assertion keys
