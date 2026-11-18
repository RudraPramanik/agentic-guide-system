## MODIFIED Requirements

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
