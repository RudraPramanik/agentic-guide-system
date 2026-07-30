## ADDED Requirements

### Requirement: Day allocator packs scored places under caps and visit budget
The project SHALL provide `src/travel_engine/day_allocator.py` with `allocate_days(selected, days, preferences=None) -> list[list[ScoredPlace]]` as locked in `docs/steps/step4.md` step 4.4.

The function MUST return exactly `days` lists. Each day MUST have `len(places) <= MAX_PLACES_PER_DAY` and `sum(visit_duration_min(p.place.category) for p in day) <= ACTIVE_DAY_VISIT_BUDGET_MIN`. Visit durations MUST go through `visit_duration_min()` — never a bare duration-dict subscript. Places that cannot fit MUST be omitted from the result (documented in the docstring). The module MUST remain pure Python with no `src.geo`, httpx, LLM, or DB I/O.

#### Scenario: Eighteen places over three days stay within caps
- **WHEN** `allocate_days` is called with 18 scored places and `days=3`
- **THEN** it returns 3 lists, each with ≤6 places, and each day’s visit-time sum is ≤ `ACTIVE_DAY_VISIT_BUDGET_MIN`

#### Scenario: Invalid days raises ValueError
- **WHEN** `allocate_days` is called with `days=0` (or any `days < 1`)
- **THEN** it raises `ValueError` with message indicating days must be `>= 1`

### Requirement: Day allocator prefers geographic clusters within CLUSTER_RADIUS_KM
`allocate_days` MUST use a pure-Python haversine helper local to the module (MUST NOT import `src.geo`) to prefer placing candidates within `CLUSTER_RADIUS_KM` of each other on the same day. Higher scores MUST be preferred when a day is full or over visit budget.

#### Scenario: Nearby places prefer the same day
- **WHEN** two high-scoring places are within `CLUSTER_RADIUS_KM` and a third is far away, with enough day capacity
- **THEN** the two nearby places are allocated to the same day more often than splitting them across days while leaving the far place with one of them

### Requirement: Day allocator purity
`day_allocator.py` MUST NOT import `src.geo`, `httpx`, litellm, qdrant, or SQLAlchemy session APIs. Distance math MUST be inline pure math only.

#### Scenario: No geo gateway imports
- **WHEN** static search is run for `src.geo` / `httpx` under `src/travel_engine/day_allocator.py`
- **THEN** there are zero matches
