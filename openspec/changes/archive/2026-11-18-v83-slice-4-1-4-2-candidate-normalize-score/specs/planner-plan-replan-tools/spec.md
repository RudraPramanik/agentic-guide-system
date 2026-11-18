## ADDED Requirements

### Requirement: build_route auto-rank uses the same travel-engine V2 gate
When `build_route` auto-ranks from `candidate_pois` because `ranked_pois` is empty, it MUST honor `TRAVEL_ENGINE_V2_ENABLED` the same way `rank_places` does: flag off ⇒ no normalizer and V2 mode off; flag on ⇒ normalize then `select_places` with V2 mode on. It MUST read the flag only through `get_settings()`. Auto-rank MUST remain a planner-tool concern; `allocate_days` and `optimize_route` stay unchanged in this change.

#### Scenario: Flag-off auto-rank matches legacy select
- **WHEN** `ranked_pois` is empty, candidates exist, and `TRAVEL_ENGINE_V2_ENABLED` is false
- **THEN** auto-rank calls selection with V2 mode off and does not normalize

#### Scenario: Flag-on auto-rank normalizes first
- **WHEN** `ranked_pois` is empty, near-duplicate candidates exist, and `TRAVEL_ENGINE_V2_ENABLED` is true
- **THEN** auto-rank normalizes before selection with V2 mode on
