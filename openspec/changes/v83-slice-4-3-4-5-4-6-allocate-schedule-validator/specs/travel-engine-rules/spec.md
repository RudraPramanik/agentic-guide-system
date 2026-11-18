## ADDED Requirements

### Requirement: Day-end constant is data
`travel_rules.py` MUST define `DAY_END_TIME` as the naive clock eight hours after `DAY_START_TIME` (`16:00` while `DAY_START_TIME` is `08:00`). `ACTIVE_DAY_VISIT_BUDGET_MIN`, `CLUSTER_RADIUS_KM`, `MAX_PLACES_PER_DAY`, and `MIN_TRAVEL_BUFFER_MIN` MUST stay at their current values unless the allocator comparison report names a miss that this change is allowed to tune. The module MUST NOT add an opening-hours parser or a timezone database.

#### Scenario: Day end is eight hours after day start
- **WHEN** `DAY_START_TIME` and `DAY_END_TIME` are read
- **THEN** `DAY_END_TIME` is `16:00` and the visit budget constant is still `8 * 60 - MIN_TRAVEL_BUFFER_MIN`

#### Scenario: Cluster radius stays 10 km
- **WHEN** `CLUSTER_RADIUS_KM` is read after this change
- **THEN** its value is `10.0` unless the comparison report recorded a named miss and the change tuned it in the same diff
