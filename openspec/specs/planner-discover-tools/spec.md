## Purpose

P5 DISCOVER-phase planner tools: readiness check, place search with geo fallback, and pure travel_engine ranking (step 5.2).

## Requirements

### Requirement: check_readiness tool
The project SHALL implement `check_readiness` registered for DISCOVER. It MUST load destination place/enrich/index counts via existing repository/service APIs and compute readiness (via `compute_readiness` or `DestinationService.get_readiness`).

If the score is below `PLANNER_MIN_READINESS_SCORE`, the tool MUST still return `ok=True` with a warning in data/message (low readiness MUST NOT block generation). DB sessions SHOULD be acquired inside the tool when needed.

#### Scenario: Low readiness is a warning
- **WHEN** readiness score is below the configured minimum
- **THEN** `ToolResult.ok` is True and the result carries a warning rather than failing hard

### Requirement: search_places tool
The project SHALL implement `search_places` registered for DISCOVER. It MUST prefer destination-scoped Qdrant `search_places` using interests/raw prefs. On empty results or search unavailable, it MUST fall back to PostGIS radius via `PlaceRepository.find_within_radius` and signal `used_geo_fallback` in `ToolResult.data`.

Mapped place rows MUST be emitted as PlaceCandidate-shaped dicts in `ToolResult.data` (for later `apply_tool_result` into `candidate_pois`). Empty soft-fail MUST use `ok=True` with a warning/code rather than raise.

When planner state has no search area, the PostGIS fallback MUST use the trip base and `SEARCH_DEFAULT_RADIUS_KM` (30), which is the current behavior.

When planner state has a search area, every emitted candidate MUST lie inside that area. Qdrant hits MUST be loaded and then dropped when they fall outside. The tool MUST NOT widen the area to recover a dropped hit. The PostGIS fallback MUST use the same area: a radius strategy MUST query the anchor latitude and longitude at that area's `radius_km`, and a boundary or polygon MUST query a covering radius derived from that geometry and then drop points outside the geometry. That fallback MUST NOT use 30 km and MUST NOT use the trip base as the center when the anchor differs. `used_geo_fallback` MUST still be true when the fallback path runs.

#### Scenario: Qdrant failure uses PostGIS fallback
- **WHEN** Qdrant search is unavailable or returns empty and PostGIS finds places and state has no search area
- **THEN** the tool returns `ok=True` with candidate data and `used_geo_fallback` set true in data

#### Scenario: Flag-off fallback stays on the 30 km base radius
- **WHEN** state has no search area and Qdrant returns no places
- **THEN** the PostGIS call uses the trip base and a 30 km radius

#### Scenario: Flag-on fallback uses the search area
- **WHEN** state has a 10 km radius area around an anchor that is not the trip base, and Qdrant returns no places
- **THEN** the PostGIS call uses the anchor and 10 km, and a place 20 km from the anchor is not a candidate

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

### Requirement: search_places forwards fusion diagnostics without changing candidate contract
The `search_places` DISCOVER tool MUST continue to prefer Qdrant results, fall back to PostGIS on empty/unavailable search, and emit PlaceCandidate-shaped dicts in `ToolResult.data.candidate_pois` with `used_geo_fallback` as today. When fusion diagnostics are present from the search layer, the tool MUST include them under a dedicated `ToolResult.data` key (e.g. `fusion_diagnostics`) and MUST NOT omit or alter `candidate_pois` because diagnostics are missing or partial. Diagnostics MUST NOT be treated as a planning merge key that replaces candidates.

When state has no search area, `candidate_pois` MUST be the hits as before. When state has a search area, `candidate_pois` MUST be those hits that fall inside the area, and `fusion_diagnostics` MUST still be attached unchanged when the search layer produced them.

#### Scenario: Candidates unchanged when diagnostics attached
- **WHEN** Qdrant returns hits, diagnostics are available, and state has no search area
- **THEN** `candidate_pois` is populated from those hits as before and `fusion_diagnostics` is present in `ToolResult.data`

#### Scenario: Geo fallback still signals used_geo_fallback
- **WHEN** Qdrant returns empty and PostGIS fallback finds places
- **THEN** `used_geo_fallback` is true and `candidate_pois` comes from geo fallback; diagnostics MAY note empty Qdrant without blocking the tool

#### Scenario: An area drops an outside hit and keeps diagnostics
- **WHEN** Qdrant returns a hit outside the search area and a hit inside it, and diagnostics are present
- **THEN** `candidate_pois` contains only the inside hit and `fusion_diagnostics` is still present

### Requirement: check_readiness forwards the trip length and still warns

`check_readiness`, and the pre-graph readiness read that copies a score onto planner state, MUST pass the trip day count into destination readiness. When the generate request includes `days`, that value MUST be used. When the generate request omits `days`, both call sites MUST pass 3, the same default `parse_preferences` already writes onto state. They MUST NOT pass 1 for an omitted generate day count, because the trip will be planned as 3 days. When `READINESS_V2_ENABLED` is false, that day count MUST NOT change the score relative to today's counter formula.

A score below `PLANNER_MIN_READINESS_SCORE` MUST still return `ok=True` with a warning. The tool MUST NOT fail the generate run because the V2 tier is `limited` or `sparse`. The tool MUST NOT add a field to the tool result beyond the keys it returns today.

#### Scenario: Three-day state is forwarded

- **WHEN** planner state has `days` equal to 3 and the readiness flag is true
- **THEN** the readiness call receives day count 3

#### Scenario: Omitted generate days uses the planner default

- **WHEN** the generate request omits `days`
- **THEN** the pre-graph readiness call and `check_readiness` both receive day count 3

#### Scenario: Low V2 score still warns

- **WHEN** the V2 score is below `PLANNER_MIN_READINESS_SCORE`
- **THEN** `ToolResult.ok` is true and the result carries a warning

#### Scenario: Flag off score ignores days

- **WHEN** the flag is false and the same destination is checked with day count 1 and day count 3
- **THEN** both calls store the same readiness score
