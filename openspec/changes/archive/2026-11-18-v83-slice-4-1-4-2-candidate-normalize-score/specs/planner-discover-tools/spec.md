## MODIFIED Requirements

### Requirement: rank_places tool
The project SHALL implement `rank_places` registered for DISCOVER. It MUST map candidates to travel_engine `PlaceCandidate` + `TripPreferences`, call `select_places` and `explain_selection` for the top `RANK_EXPLANATION_TOP_N` (named constant, default 5), and emit ranked POIs via `ToolResult.data`. Ranking MUST be pure (no LLM).

`rank_places` MUST read `TRAVEL_ENGINE_V2_ENABLED` only through `get_settings()`. When the flag is false, it MUST NOT call the candidate normalizer and MUST call `select_places` with V2 mode off so output matches today's path. When the flag is true, it MUST normalize candidates first, then call `select_places` with V2 mode on, and MUST include explanations that may list V2 breakdown keys. It MUST NOT change HTTP, SSE, or `ToolResult` field names.

#### Scenario: Ranking uses travel_engine only
- **WHEN** `rank_places` runs with candidates and preferences
- **THEN** it returns ranked places without importing litellm or calling the LLM gateway

#### Scenario: Flag off skips the normalizer
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is false
- **THEN** `rank_places` does not normalize candidates and scores with V2 mode off

#### Scenario: Flag on normalizes then scores V2
- **WHEN** `TRAVEL_ENGINE_V2_ENABLED` is true and near-duplicate monastery variants are in candidates
- **THEN** `rank_places` returns a ranked list after normalization and V2 scoring
