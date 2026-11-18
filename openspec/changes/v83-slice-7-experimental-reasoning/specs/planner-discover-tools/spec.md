## MODIFIED Requirements

### Requirement: rank_places tool
The project SHALL implement `rank_places` registered for DISCOVER. It MUST map candidates to travel_engine `PlaceCandidate` + `TripPreferences`, call `select_places` and `explain_selection` for the top `RANK_EXPLANATION_TOP_N` (named constant, default 5), and emit ranked POIs via `ToolResult.data`.

`rank_places` MUST read `TRAVEL_ENGINE_V2_ENABLED` and `REASONING_LAYER_ENABLED` only through `get_settings()`. When `REASONING_LAYER_ENABLED` is false, ranking MUST be pure: it MUST NOT call the LLM gateway and MUST NOT import `litellm`. When `REASONING_LAYER_ENABLED` is true, `rank_places` MAY call the experience reasoner after candidates exist and before ranking. A skipped or failed reasoner MUST leave an empty priority map. The tool MUST then rank with `rank_candidates` and that map. It MUST still not import `litellm`.

When `TRAVEL_ENGINE_V2_ENABLED` is false, it MUST NOT call the candidate normalizer and MUST call `select_places` with V2 mode off so output matches today's path when the priority map is empty. When `TRAVEL_ENGINE_V2_ENABLED` is true, it MUST normalize candidates first, then call `select_places` with V2 mode on, and MUST include explanations that may list V2 breakdown keys. It MUST NOT change HTTP, SSE, or `ToolResult` field names. `ToolResult.data` MUST stay `ranked_pois` and `explanations` only.

#### Scenario: Ranking uses travel_engine only
- **WHEN** `rank_places` runs with candidates and preferences and `REASONING_LAYER_ENABLED` is false
- **THEN** it returns ranked places without importing litellm or calling the LLM gateway

#### Scenario: Flag off skips the normalizer
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false and `REASONING_LAYER_ENABLED` is false
- **THEN** `rank_places` does not normalize candidates and scores with V2 mode off

#### Scenario: Flag on normalizes then scores V2
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and near-duplicate monastery variants are in candidates and `REASONING_LAYER_ENABLED` is false
- **THEN** `rank_places` returns a ranked list after normalization and V2 scoring

#### Scenario: Layer on still returns the same tool fields
- **WHEN** `REASONING_LAYER_ENABLED` is true and the reasoner returns a valid priority for one known candidate
- **THEN** `ToolResult.data` contains only `ranked_pois` and `explanations`, and a reasoner failure still returns those fields from unboosted ranking
