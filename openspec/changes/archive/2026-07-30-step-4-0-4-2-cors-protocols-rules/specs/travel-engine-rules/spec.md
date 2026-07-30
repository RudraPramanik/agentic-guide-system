## ADDED Requirements

### Requirement: travel_rules split structural and interest vocabularies
The project SHALL provide `src/travel_engine/travel_rules.py` with constants exactly as locked in `docs/steps/step4.md` step 4.2, including:
- Caps/times: `MAX_PLACES_PER_DAY=6`, travel/lunch/day-start constants, `ACTIVE_DAY_VISIT_BUDGET_MIN`, `CLUSTER_RADIUS_KM`, `GEO_COHERENCE_MAX_STDDEV_KM`, `ANCHOR_MIN_SCORE`, `MAX_ROUTE_DROP_ATTEMPTS`, `BASE_SENTINEL_ID`
- Structural: `VISIT_DURATION_BY_CATEGORY` covering all P2 categories (`museum|viewpoint|monastery|attraction|park|trailhead`), `VISIT_DURATION_DEFAULT_MIN=30`, `MORNING_ONLY_CATEGORIES=["viewpoint"]` (no `sunrise_point`), `AVOID_SAME_DAY_PAIRS`
- Interest: `CATEGORY_WEIGHTS` keys ⊆ `PLACE_TAG_VOCAB`
- `visit_duration_min(category)` using `.get(..., VISIT_DURATION_DEFAULT_MIN)`

Interest-only tags (`trek`, `cultural`, …) MUST NOT appear as keys in `VISIT_DURATION_BY_CATEGORY`. The module MUST NOT perform I/O or import geo/LLM/DB clients.

#### Scenario: Duration keys cover P2 categories
- **WHEN** `VISIT_DURATION_BY_CATEGORY` is inspected
- **THEN** its keys are a superset of `{museum, viewpoint, monastery, attraction, park, trailhead}`

#### Scenario: Unknown category uses default
- **WHEN** `visit_duration_min("unknown_future")` is called
- **THEN** the result is `30` and no `KeyError` is raised

#### Scenario: Interest weights stay within PLACE_TAG_VOCAB
- **WHEN** `CATEGORY_WEIGHTS` keys are compared to `PLACE_TAG_VOCAB`
- **THEN** every weight key is present in the vocab

#### Scenario: Dead and conflated keys are absent
- **WHEN** morning-only and duration maps are inspected
- **THEN** `sunrise_point` is not in `MORNING_ONLY_CATEGORIES` and `trek` is not in `VISIT_DURATION_BY_CATEGORY`
