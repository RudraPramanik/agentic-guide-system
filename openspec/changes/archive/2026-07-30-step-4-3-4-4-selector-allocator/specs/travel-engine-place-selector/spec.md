## ADDED Requirements

### Requirement: Place selector scores by sum of matching interest weights
The project SHALL provide `src/travel_engine/place_selector.py` with pure types `PlaceCandidate`, `TripPreferences`, `ScoredPlace` and functions `score_place`, `explain_selection`, and `select_places` as locked in `docs/steps/step4.md` step 4.3.

Scoring MUST be the **sum** of `CATEGORY_WEIGHTS[tag]` for every tag present in both `place.enriched_tags` and the user’s interests (and present in `CATEGORY_WEIGHTS`). Unknown tags MUST contribute `0` without raising. Empty `enriched_tags` MUST yield score `0` and remain selectable. Budget on `TripPreferences` MUST be soft-only (no hard exclude). The module MUST NOT import SQLAlchemy models, `src.geo`, httpx, LLM, or DB clients. Morning-only placement MUST NOT be enforced here.

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
