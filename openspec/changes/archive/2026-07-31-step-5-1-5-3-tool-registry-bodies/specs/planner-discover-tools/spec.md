## ADDED Requirements

### Requirement: check_readiness tool
The project SHALL implement `check_readiness` registered for DISCOVER. It MUST load destination place/enrich/index counts via existing repository/service APIs and compute readiness (via `compute_readiness` or `DestinationService.get_readiness`).

If the score is below `PLANNER_MIN_READINESS_SCORE`, the tool MUST still return `ok=True` with a warning in data/message (low readiness MUST NOT block generation). DB sessions SHOULD be acquired inside the tool when needed.

#### Scenario: Low readiness is a warning
- **WHEN** readiness score is below the configured minimum
- **THEN** `ToolResult.ok` is True and the result carries a warning rather than failing hard

### Requirement: search_places tool
The project SHALL implement `search_places` registered for DISCOVER. It MUST prefer destination-scoped Qdrant `search_places` using interests/raw prefs. On empty results or search unavailable, it MUST fall back to PostGIS radius via `PlaceRepository.find_within_radius` and signal `used_geo_fallback` in `ToolResult.data`.

Mapped place rows MUST be emitted as PlaceCandidate-shaped dicts in `ToolResult.data` (for later `apply_tool_result` into `candidate_pois`). Empty soft-fail MUST use `ok=True` with a warning/code rather than raise.

#### Scenario: Qdrant failure uses PostGIS fallback
- **WHEN** Qdrant search is unavailable or returns empty and PostGIS finds places
- **THEN** the tool returns `ok=True` with candidate data and `used_geo_fallback` set true in data

### Requirement: rank_places tool
The project SHALL implement `rank_places` registered for DISCOVER. It MUST map candidates to travel_engine `PlaceCandidate` + `TripPreferences`, call `select_places` and `explain_selection` for the top `RANK_EXPLANATION_TOP_N` (named constant, default 5), and emit ranked POIs via `ToolResult.data`. Ranking MUST be pure (no LLM).

#### Scenario: Ranking uses travel_engine only
- **WHEN** `rank_places` runs with candidates and preferences
- **THEN** it returns ranked places without importing litellm or calling the LLM gateway
