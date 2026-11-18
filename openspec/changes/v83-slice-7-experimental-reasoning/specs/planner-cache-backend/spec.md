## MODIFIED Requirements

### Requirement: Planner MVP cache key and TravelState subset
Planner cache helpers MUST compute the locked MVP key:

`sha256(f"{destination_id}:{sha256(normalized_raw_input)}:{days_or_0}:{round(base_lat,3)}:{round(base_lng,3)}")`

where `normalized_raw_input` is `PlanRequest.raw_input` with strip + collapsed internal whitespace, and `days_or_0` is `PlanRequest.days` if set else `0`. TTL MUST come from `PLANNER_CACHE_TTL_SECONDS`.

When `REASONING_LAYER_ENABLED` is false, the hashed material MUST be that formula, plus the location suffix this helper already appends when the suffix is non-empty. No reasoning suffix is added. When `REASONING_LAYER_ENABLED` is true, the hashed material MUST add `:reasoning-v1` after that same base, so a reasoned trip does not share a cache entry with a flag-off trip. Shadow sampling MUST NOT add this suffix, because the saved and cached itinerary is the control itinerary.

Cached values MUST be a JSON-serializable subset of final `TravelState` sufficient for SSE display and `TripService.save_from_state`, including at least `schedule` (with `leg_polyline`/`day_polyline`), `itinerary`, preference fields (`interests`, `budget`, `include_offbeat`, `include_trekking`, `days`), `destination_id`, and completion flags (`plan_complete`, `abort_triggered`). Preference-semantic keys (`interests`/`budget` after parse) MUST NOT be used as the primary key in P6. The cache subset MUST NOT be required to store reasoning trace entries.

#### Scenario: Key includes rounded base coords and normalized raw_input
- **WHEN** two PlanRequests differ only by whitespace in `raw_input` or base coords within the same 0.001° rounding bucket, and `REASONING_LAYER_ENABLED` is false
- **THEN** they resolve to the same cache key

#### Scenario: Different days produce different keys
- **WHEN** two otherwise identical requests differ in `days` (including None vs a set value), and `REASONING_LAYER_ENABLED` is false
- **THEN** they resolve to different cache keys

#### Scenario: Flag off matches the key without a reasoning suffix
- **WHEN** `REASONING_LAYER_ENABLED` is false and no location suffix is present
- **THEN** the cache key equals the hash of the locked MVP formula with no `:reasoning-v1` segment

#### Scenario: Flag on does not reuse the flag-off entry
- **WHEN** the same destination, text, days, and base are cached once with `REASONING_LAYER_ENABLED` false and once with it true
- **THEN** the two cache keys differ
