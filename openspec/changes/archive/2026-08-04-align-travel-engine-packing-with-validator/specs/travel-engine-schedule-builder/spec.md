## MODIFIED Requirements

### Requirement: Schedule builder enforces morning-only early slots
Before final timing, when any stop’s structural `category` is in `MORNING_ONLY_CATEGORIES`, `build_day_schedule` MUST stable-extract morning-only stops toward the front (preserving relative order among them), placing at most two in the earliest slots. Excess morning-only stops beyond two MUST NOT be scheduled in slots that would violate order ≤ 2 (MUST be omitted from the timed day list, with the algorithm documented). The function MUST then time the day so retained morning-only stops occupy order ≤ 2. The module MUST document this algorithm. When a morning extract changes stop order, legs MUST either already match the adjusted order or supply a lookup-complete set; otherwise the function MUST raise `ValueError` with a clear domain message (MUST NOT call geo/OSRM).

#### Scenario: Viewpoint lands in morning slot
- **WHEN** a day’s stops include a `viewpoint` and legs match the morning-adjusted order (lookup-complete)
- **THEN** that viewpoint appears in stop order 1 or 2 with `suggested_start_time <= "10:30"` when base→first travel allows

#### Scenario: Excess morning-only beyond two are omitted from timed day
- **WHEN** `ordered_stops` contains three or more morning-only category places and lookup-complete legs
- **THEN** the returned schedule contains at most two morning-only stops, both in order 1–2, and does not place a third morning-only stop later in the day
