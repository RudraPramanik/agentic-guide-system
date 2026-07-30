## ADDED Requirements

### Requirement: Travel engine has no I/O

The `src/travel_engine` package MUST NOT import LLM clients, httpx, SQLAlchemy sessions, Qdrant, or `src.geo`. Routing times MUST be supplied only via an injected `RoutingProvider`.

#### Scenario: Import purity
- **WHEN** a static check or unit test imports `src.travel_engine` modules
- **THEN** those modules MUST NOT transitively require network or database connectivity to load

### Requirement: RoutingProvider protocol

The system MUST define a `RoutingProvider` protocol with an async `travel_matrix(waypoints: list[tuple[UUID, float, float]]) -> list[RouteLeg]` method, and a `RouteLeg` model carrying `from_place_id`, `to_place_id`, `duration_min`, `distance_km`, and `used_fallback`.

#### Scenario: Fake provider drives optimizer tests
- **WHEN** `optimize_route` is called with a `FakeRoutingProvider` that returns fixed legs
- **THEN** the optimizer MUST complete without any network call and MUST produce an ordered stop list

### Requirement: Structural vs interest vocabulary

`VISIT_DURATION_BY_CATEGORY` and `MORNING_ONLY_CATEGORIES` MUST be keyed only by P2 `Place.category` values (`museum`, `viewpoint`, `monastery`, `attraction`, `park`, `trailhead`). `CATEGORY_WEIGHTS` MUST be keyed only by P3 `PLACE_TAG_VOCAB` interest tags. `MORNING_ONLY_CATEGORIES` MUST NOT include `sunrise_point`. Duration map MUST include `attraction` and `trailhead`. Duration lookups MUST use `.get(category, VISIT_DURATION_DEFAULT_MIN)`.

#### Scenario: Common attraction category has a duration
- **WHEN** visit duration is resolved for `place.category == "attraction"`
- **THEN** the result MUST be the configured attraction minutes, not the default-only path and not a KeyError

#### Scenario: Interest tag is not used as category duration key
- **WHEN** rules are loaded
- **THEN** `VISIT_DURATION_BY_CATEGORY` MUST NOT contain interest-only keys such as `trek` or `cultural`

### Requirement: Place selection scoring

`select_places` MUST score each candidate as the sum of `CATEGORY_WEIGHTS[tag]` for every tag that is in both `place.enriched_tags` and the user interests (and present in `CATEGORY_WEIGHTS`). It MUST apply conflict rules from `AVOID_SAME_DAY_PAIRS` and MUST expose `explain_selection` returning a human-readable string suitable for tool-trace logging (not a new TripEvaluation column).

#### Scenario: Multi-interest outranks single interest
- **WHEN** place A matches two requested interests and place B matches one, with otherwise equal candidates
- **THEN** place A MUST receive a higher score than place B

#### Scenario: Explain selection is trace-shaped
- **WHEN** `explain_selection` is called for a scored place
- **THEN** it MUST return a non-empty string summarizing why the place scored (tags/weights), without requiring a DB write

### Requirement: Day allocation caps

`allocate_days` MUST distribute selected places across N days with at most `MAX_PLACES_PER_DAY` per day, respect visit-duration budgets using structural category durations, and prefer geographic pre-clustering of nearby places into the same day candidate pool.

#### Scenario: Three-day split respects caps
- **WHEN** 18 scored places are allocated across 3 days
- **THEN** each day list MUST have length ≤ `MAX_PLACES_PER_DAY` and total visit time within the configured daily active budget

### Requirement: Route optimization with drop-retry

`optimize_route` MUST order a day's stops to minimize total travel time using the injected routing matrix, MUST start from `base_lat`/`base_lng`, MUST use exhaustive permutation search when stop count ≤ `MAX_PLACES_PER_DAY`, and MUST NOT depend on a TSP solver package. If total travel exceeds `MAX_DAILY_TRAVEL_MIN`, it MUST drop the lowest-scored stop and retry up to 3 times, returning any dropped stops with reasons on the result.

#### Scenario: Over-budget day drops weakest stop
- **WHEN** every ordering exceeds `MAX_DAILY_TRAVEL_MIN` with the full stop set
- **THEN** the result MUST omit at least one stop, include that stop in `dropped_stops` with a reason, and attempt at most 3 drop retries

#### Scenario: No external TSP dependency
- **WHEN** route optimization is implemented
- **THEN** the codebase MUST NOT add a TSP solver package solely for day ordering

### Requirement: Schedule builder wall-clock times

`build_day_schedule` MUST assign naive local wall-clock `suggested_start_time` strings using `DAY_START_TIME`, insert a lunch break when the day spans `LUNCH_BREAK_START`, force morning-only categories into early slots (order ≤ 2 / start ≤ configured morning cutoff), and MUST NOT attach timezones or convert to UTC.

#### Scenario: Morning viewpoint placement
- **WHEN** a day includes a `viewpoint` stop among up to 6 ordered stops
- **THEN** that stop MUST appear in schedule slot 1 or 2 with `suggested_start_time` at or before the morning cutoff

### Requirement: Trip validation rules

`validate_trip` MUST return `ValidationResult(passed, warnings, errors)` checking at least: daily travel ≤ `MAX_DAILY_TRAVEL_MIN`, no place repeated across days, morning-only places in morning slots, at least one anchor attraction per day (score above configured threshold), and geographic coherence against a named rules constant.

#### Scenario: Good itinerary passes
- **WHEN** a coherent multi-day itinerary meeting all rules is validated
- **THEN** `errors` MUST be empty and `passed` MUST be true

#### Scenario: Injected violation is specific
- **WHEN** an itinerary repeats the same place on two days
- **THEN** `errors` MUST include a message identifying the repetition rule failure
