## ADDED Requirements

### Requirement: search_places forwards fusion diagnostics without changing candidate contract
The `search_places` DISCOVER tool MUST continue to prefer Qdrant results, fall back to PostGIS on empty/unavailable search, and emit PlaceCandidate-shaped dicts in `ToolResult.data.candidate_pois` with `used_geo_fallback` as today. When fusion diagnostics are present from the search layer, the tool MUST include them under a dedicated `ToolResult.data` key (e.g. `fusion_diagnostics`) and MUST NOT omit or alter `candidate_pois` because diagnostics are missing or partial. Diagnostics MUST NOT be treated as a planning merge key that replaces candidates.

#### Scenario: Candidates unchanged when diagnostics attached
- **WHEN** Qdrant returns hits and diagnostics are available
- **THEN** `candidate_pois` is populated from those hits as before and `fusion_diagnostics` is present in `ToolResult.data`

#### Scenario: Geo fallback still signals used_geo_fallback
- **WHEN** Qdrant returns empty and PostGIS fallback finds places
- **THEN** `used_geo_fallback` is true and `candidate_pois` comes from geo fallback; diagnostics MAY note empty Qdrant without blocking the tool
