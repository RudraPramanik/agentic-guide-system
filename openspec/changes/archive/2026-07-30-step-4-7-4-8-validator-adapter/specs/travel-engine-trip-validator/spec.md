## ADDED Requirements

### Requirement: Trip validator returns ValidationResult via named rule chain
The project SHALL provide `src/travel_engine/trip_validator.py` with Pydantic types `ValidationResult`, `DayPlan`, `TripItinerary`, and function `validate_trip(itinerary: TripItinerary) -> ValidationResult` as locked in `docs/steps/step4.md` step 4.7 and `docs/blueprint_final.md` v6.1.

`validate_trip` MUST evaluate these check functions in order (Chain of Responsibility — one function per rule), extending an errors list with each function’s returned messages:
1. `check_daily_travel_cap`
2. `check_no_repeat_places`
3. `check_morning_slots`
4. `check_anchor_per_day`
5. `check_geo_coherence`

`passed` MUST be `True` iff `errors` is empty. The module MUST import neither `src.geo`, httpx, LLM clients, SQLAlchemy, nor Qdrant. Merely-invalid travel plans MUST return errors — MUST NOT raise (except programmer errors such as `None` itinerary / Pydantic validation failure).

#### Scenario: Good itinerary passes
- **WHEN** a fixture itinerary satisfies all rules
- **THEN** `errors` is empty, `passed` is true, and no network/DB I/O occurs

#### Scenario: Empty itinerary fails with locked code
- **WHEN** `validate_trip` is called with `TripItinerary(days=[])`
- **THEN** the result has `passed=False` and `errors` contains `"empty_itinerary"`

### Requirement: Daily travel cap and no-repeat place checks
`check_daily_travel_cap` MUST append an error (including day index) when a day’s `total_travel_min` exceeds `MAX_DAILY_TRAVEL_MIN` from `travel_rules`.

`check_no_repeat_places` MUST append an error when the same place id appears more than once across all stops in the itinerary (include place id or name when useful).

#### Scenario: Over-cap day produces a specific error
- **WHEN** a day has `total_travel_min` greater than `MAX_DAILY_TRAVEL_MIN`
- **THEN** `errors` contains a message identifying that day and the travel-cap violation

#### Scenario: Repeated place produces a specific error
- **WHEN** the same place id appears on two stops in the itinerary
- **THEN** `errors` contains a distinct no-repeat message (not a single opaque failure shared with other rules)

### Requirement: Morning slot, anchor, and geo-coherence checks
`check_morning_slots` MUST error when any stop whose structural `place.category` is in `MORNING_ONLY_CATEGORIES` is outside stop order ≤ 2 or has `suggested_start_time` after `MORNING_SLOT_LATEST_START`.

`check_anchor_per_day` MUST error when a day has no stop with `score > ANCHOR_MIN_SCORE`.

`check_geo_coherence` MUST error when a day’s stop-coordinate sample standard deviation (km) exceeds `GEO_COHERENCE_MAX_STDDEV_KM`. The threshold MUST come from `travel_rules` — no magic number in the check body. Days with fewer than two stops MUST NOT fail geo coherence.

#### Scenario: Late morning-only stop errors
- **WHEN** a viewpoint (or other morning-only category) is scheduled after slot 2 or starts after `MORNING_SLOT_LATEST_START`
- **THEN** `errors` contains a morning-slot-specific message including day and place context

#### Scenario: Day without anchor errors
- **WHEN** every stop on a day has `score <= ANCHOR_MIN_SCORE`
- **THEN** `errors` contains an anchor-specific message for that day

#### Scenario: Spread-out day fails geo coherence
- **WHEN** a day’s stops have coordinate sample std-dev (km) above `GEO_COHERENCE_MAX_STDDEV_KM`
- **THEN** `errors` contains a geo-coherence message for that day

### Requirement: Dropped stops surface as REPLAN warning only
When any `DayPlan.dropped_stops` is non-empty, `validate_trip` MUST append the warning token `one_or_more_days_already_dropped_stops_prefer_expand_poi_search`. Dropped stops MUST NOT by themselves set `passed=False` or add to `errors`. The validator MUST NOT call REPLAN tools.

#### Scenario: Prior drops warn without failing
- **WHEN** a otherwise-valid itinerary has at least one day with non-empty `dropped_stops`
- **THEN** `passed` is true, `errors` is empty, and `warnings` contains `one_or_more_days_already_dropped_stops_prefer_expand_poi_search`
