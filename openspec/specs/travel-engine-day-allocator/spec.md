## Purpose

Pure day packing for the travel engine (P4 step 4.4): cluster geographically and respect place caps + visit-time budget.

## Requirements

### Requirement: Day allocator packs scored places under caps and visit budget
The project SHALL provide `src/travel_engine/day_allocator.py` with `allocate_days(selected, days, preferences=None) -> list[list[ScoredPlace]]` as locked in `docs/steps/step4.md` step 4.4.

The function MUST return exactly `days` lists. Each day MUST have `len(places) <= MAX_PLACES_PER_DAY` and `sum(visit_duration_min(p.place.category) for p in day) <= ACTIVE_DAY_VISIT_BUDGET_MIN`. Visit durations MUST go through `visit_duration_min()` — never a bare duration-dict subscript. Places that cannot fit MUST be omitted from the result (documented in the docstring). Each day MUST also satisfy the morning-only per-day cap (≤2). The module MUST remain pure Python with no `src.geo`, httpx, LLM, or DB I/O.

#### Scenario: Eighteen places over three days stay within caps
- **WHEN** `allocate_days` is called with 18 scored places and `days=3`
- **THEN** it returns 3 lists, each with ≤6 places, each day’s visit-time sum is ≤ `ACTIVE_DAY_VISIT_BUDGET_MIN`, and each day has ≤2 morning-only category places

#### Scenario: Invalid days raises ValueError
- **WHEN** `allocate_days` is called with `days=0` (or any `days < 1`)
- **THEN** it raises `ValueError` with message indicating days must be `>= 1`

### Requirement: Day allocator caps morning-only stops per day
`allocate_days` MUST NOT place more than two stops whose structural `category` is in `MORNING_ONLY_CATEGORIES` onto the same day. When a candidate would exceed that cap on the preferred day, the allocator MUST try another day that can accept it under existing place/visit/morning caps, or omit the candidate if no day can accept it. The module MUST remain pure (no `src.geo` / httpx / LLM / DB).

#### Scenario: Third viewpoint is not packed onto a day that already has two
- **WHEN** `allocate_days` is called with at least three `viewpoint` scored places and enough non-morning filler for multiple days
- **THEN** no returned day list contains more than two places with category in `MORNING_ONLY_CATEGORIES`

### Requirement: Day allocator soft geo spill prefers nearer day centroids
When a place cannot join its preferred cluster day and must spill, `allocate_days` MUST prefer an underfilled day whose current centroid is geographically nearer to the candidate (pure haversine in-module) over a farther underfilled day, all else equal on capacity. The allocator MUST NOT hard-reject a candidate solely because a projected geo-coherence sample stddev would exceed `GEO_COHERENCE_MAX_STDDEV_KM` (soft packing only).

#### Scenario: Spill chooses the nearer underfilled day
- **WHEN** the preferred day is full and two other days have capacity — one whose centroid is near the candidate and one far
- **THEN** the candidate is placed on the nearer day’s list when both days otherwise can accept it

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
