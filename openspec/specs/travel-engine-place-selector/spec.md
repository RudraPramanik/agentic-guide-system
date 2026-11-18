## Purpose

Pure place scoring and selection for the travel engine (P4 step 4.3). No I/O; maps from ORM Place at the tool/service boundary later.

## Requirements

### Requirement: Place selector scores by sum of matching interest weights
The project SHALL provide `src/travel_engine/place_selector.py` with pure types `PlaceCandidate`, `TripPreferences`, `ScoredPlace` and functions `score_place`, `explain_selection`, and `select_places` as locked in `docs/steps/step4.md` step 4.3, extended only by the additive optional fields and injected V2 mode defined in this change.

With V2 mode off (the default path), scoring MUST be the **sum** of `CATEGORY_WEIGHTS[tag]` for every tag present in both `place.enriched_tags` and the user’s interests (and present in `CATEGORY_WEIGHTS`). Unknown tags MUST contribute `0` without raising. Empty `enriched_tags` MUST yield score `0` and remain selectable. Budget on `TripPreferences` MUST be soft-only (no hard exclude). The module MUST NOT import SQLAlchemy models, `src.geo`, httpx, LLM, DB clients, or `get_settings()`. Morning-only placement MUST NOT be enforced here.

#### Scenario: Multi-interest outranks single interest
- **WHEN** `select_places` is called with one place matching two requested interests and another matching one
- **THEN** the multi-interest place ranks first with a strictly higher score

#### Scenario: Empty enriched_tags scores zero
- **WHEN** a candidate has `enriched_tags=[]`
- **THEN** its score is `0`, it appears in the result, and no exception is raised

#### Scenario: Empty candidates or empty interests do not raise
- **WHEN** candidates are `[]` OR interests are `[]`
- **THEN** the result is `[]` or an all-zero-scored list respectively, with no exception

### Requirement: Place selector applies greedy AVOID_SAME_DAY_PAIRS filter
`select_places` MUST sort by score descending (stable tie-break by name/id), then greedily keep higher-scored places and drop a candidate when its structural `category` would form a forbidden pair with any already-kept place per `AVOID_SAME_DAY_PAIRS` (including same-category pairs such as monastery–monastery). The greedy keep-higher-score rule MUST be documented in the module docstring.

#### Scenario: Conflicting monastery pair drops the lower score
- **WHEN** two monastery candidates are scored and `AVOID_SAME_DAY_PAIRS` includes `("monastery", "monastery")`
- **THEN** only the higher-scored monastery remains in the selected list

### Requirement: explain_selection returns compact trace strings
`explain_selection(place, score_breakdown)` MUST return a single compact string suitable for tool_trace / future `rank_places` explanations (e.g. name, total score, and contributing tag=weight pairs). It MUST NOT imply a new DB column or migration.

#### Scenario: Explanation includes name and breakdown
- **WHEN** `explain_selection` is called with a non-empty score breakdown
- **THEN** the returned string includes the place name and at least one contributing tag weight

### Requirement: PlaceCandidate may carry optional V2 fields without breaking legacy dicts
`PlaceCandidate` MUST keep the existing required fields including `id` (not renamed). It MAY add optional fields used by normalization and evidence-aware scoring (`source`, `source_id`, `aliases`, `parent_place_id`, `user_selected`, and an evidence presence/ref list). All new fields MUST default so existing candidate dicts that only carry today's keys still validate. The module MUST NOT introduce a second candidate type.

#### Scenario: Legacy candidate dict still validates
- **WHEN** a dict with only `id`, `name`, `category`, `enriched_tags`, `lat`, and `lng` is validated as `PlaceCandidate`
- **THEN** validation succeeds and optional V2 fields take their defaults

### Requirement: V2 scoring adds configured terms on an injected mode
When selection runs with V2 mode enabled, scoring MUST keep the v6.1 sum of matching `CATEGORY_WEIGHTS` as the base and MUST add configured terms from `travel_rules` for diversity, geo fit, evidence, and duplicate penalty. Each contributing term MUST appear in `score_breakdown` under a stable key. When V2 mode is disabled, scoring MUST equal today's sum-of-matching-weights path (byte-identical totals and breakdown keys for the same inputs). The selector MUST receive V2 mode as an injected argument or equivalent pure parameter; it MUST NOT call `get_settings()` or embed the string `TRAVEL_ENGINE_V2_ENABLED`.

#### Scenario: Flag-off scoring matches v6.1
- **WHEN** the same candidates and interests are scored with V2 mode off
- **THEN** totals and interest-tag breakdown keys match the pre-change sum-of-matching-weights behavior

#### Scenario: V2 terms appear in the breakdown
- **WHEN** V2 mode is on and configured term weights are non-zero
- **THEN** `score_breakdown` includes the configured V2 term keys in addition to matching interest tags

#### Scenario: Missing evidence scores zero for that term
- **WHEN** V2 mode is on and a candidate has no evidence refs
- **THEN** the evidence term contributes `0` and selection does not raise

### Requirement: explain_selection includes V2 breakdown keys
`explain_selection` MUST remain a single compact string for tool_trace. When the breakdown contains V2 term keys, the string MUST include those keys and values alongside interest weights. It MUST NOT imply a new DB column, HTTP field, or SSE event.

#### Scenario: Explanation lists a V2 term
- **WHEN** `explain_selection` is called with a breakdown that includes a V2 term key
- **THEN** the returned string includes that key and its numeric contribution

### Requirement: PlaceCandidate preserves raw hours and does not parse them

`PlaceCandidate` MUST accept an optional `opening_hours_raw` string defaulting to null. Existing candidate dicts that omit the field MUST still validate. Scoring and selection MUST ignore `opening_hours_raw`, `opening_hours_status`, `opening_open`, and `opening_close`. The selector module MUST NOT parse an OSM hours string and MUST NOT add a parser dependency. The travel engine MUST NOT read `READINESS_V2_ENABLED`.

#### Scenario: Legacy candidate dict still validates without raw hours

- **WHEN** a dict with only `id`, `name`, `category`, `enriched_tags`, `lat`, and `lng` is validated as `PlaceCandidate`
- **THEN** validation succeeds and `opening_hours_raw` is null

#### Scenario: Hours fields do not change the score

- **WHEN** two candidates differ only in `opening_hours_raw` and `opening_hours_status`
- **THEN** their scores are equal
