## Purpose

Pure wall-clock day scheduling for the travel engine (P4 step 4.6). Naive `"HH:MM"` only; no timezone/UTC conversion and no I/O.

## Requirements

### Requirement: Schedule builder assigns naive wall-clock start times
The project SHALL provide `src/travel_engine/schedule_builder.py` with type `ScheduledStop` and function `build_day_schedule(ordered_stops, route_legs) -> list[ScheduledStop]` as locked in `docs/steps/step4.md` step 4.6 and `docs/blueprint_final.md` v6.1.

`build_day_schedule` MUST:
- Return `[]` when `ordered_stops` is empty
- Use destination-local naive `"HH:MM"` strings only — MUST NOT attach timezones or convert to UTC
- Start the running clock at `DAY_START_TIME`
- Set each stop’s `visit_duration_min` via `visit_duration_min(category)` (never bare duration-dict subscript)
- Advance the clock by visit duration and by travel from matching legs between consecutive stops
- Insert a `LUNCH_BREAK_MIN` gap when adding the next visit would cross `LUNCH_BREAK_START` (MAY set `arrival_note` mentioning lunch)
- Remain pure: no LLM, network, DB, or `src.geo` imports

#### Scenario: Six-stop day gets start times from 08:00
- **WHEN** `build_day_schedule` is called with six ordered stops and matching consecutive `route_legs`
- **THEN** every stop has a `suggested_start_time`, and the first stop’s time is `>= "08:00"`

#### Scenario: Lunch gap when spanning lunch start
- **WHEN** the running schedule would place the next visit such that it crosses `LUNCH_BREAK_START`
- **THEN** a lunch gap of `LUNCH_BREAK_MIN` is inserted before that visit

### Requirement: Schedule builder enforces morning-only early slots
Before final timing, when any stop’s structural `category` is in `MORNING_ONLY_CATEGORIES`, `build_day_schedule` MUST stable-extract morning-only stops toward the front (preserving relative order among them), placing at most two in the earliest slots, then time the day so morning-only stops occupy order ≤ 2 with `suggested_start_time <= MORNING_SLOT_LATEST_START` when enough early slots exist. The module MUST document this algorithm. When a morning extract changes stop order, legs MUST either already match the adjusted order or supply a lookup-complete set; otherwise the function MUST raise `ValueError` with a clear domain message (MUST NOT call geo/OSRM).

#### Scenario: Viewpoint lands in morning slot
- **WHEN** a day’s stops include a `viewpoint` and legs match the morning-adjusted order
- **THEN** that viewpoint appears in stop order 1 or 2 with `suggested_start_time <= "10:30"`

### Requirement: Schedule builder rejects mismatched consecutive legs
For the common optimizer→schedule path, when `ordered_stops` is non-empty, `build_day_schedule` MUST require `len(route_legs) == len(ordered_stops)` for consecutive base→first… hops (or a larger lookup-complete leg list as documented). On mismatch that cannot time the day, it MUST raise `ValueError` with a clear message — not an HTTP error and not a silent wrong schedule.

#### Scenario: Too few legs raises ValueError
- **WHEN** `ordered_stops` has N≥1 stops and `route_legs` length is incompatible with timing that order
- **THEN** `build_day_schedule` raises `ValueError`
