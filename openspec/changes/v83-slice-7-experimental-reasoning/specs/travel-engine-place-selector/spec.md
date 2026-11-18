## ADDED Requirements

### Requirement: Optional priority boosts do not change an empty map
`select_places` and `rank_candidates` MUST accept an optional priority map from place id to `high`, `medium`, or `low`. When the map is omitted or empty, scores, sort order, and score breakdown keys MUST match the call without that argument, for both V2 mode off and V2 mode on. The module MUST NOT import an LLM client, `src.planner`, or `get_settings()`.

When the map is non-empty, a listed place MUST receive one non-negative boost from fixed weights in `travel_rules.py`. `high` MUST be strictly less than the smallest positive `CATEGORY_WEIGHTS` value. `medium` MUST be strictly less than `high`. `low` MUST be 0. An id that is not in the candidate list MUST be ignored. The boost MUST appear in the score breakdown only for a place that has a priority. Interest-weight scoring MUST still run and MUST remain the base score.

#### Scenario: An empty map matches today's scores
- **WHEN** `select_places` is called twice with the same candidates and interests, once with no priority map and once with an empty map, and V2 mode is off
- **THEN** the scores, order, and breakdown keys are identical

#### Scenario: A high priority cannot replace an interest match
- **WHEN** one place matches one positive interest tag and has no priority, and another place matches no interest and has priority `high`
- **THEN** the interest match ranks strictly above the high-priority place

#### Scenario: The engine does not call a model
- **WHEN** import checks scan `src/travel_engine/place_selector.py` and `src/travel_engine/travel_rules.py`
- **THEN** neither file imports `src.planner.reasoning` or an LLM client
