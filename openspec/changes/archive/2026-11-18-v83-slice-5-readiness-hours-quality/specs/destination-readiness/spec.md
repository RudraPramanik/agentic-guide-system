## MODIFIED Requirements

### Requirement: DestinationService get_readiness uses compute_readiness

The system SHALL implement `DestinationService.get_readiness(destination_id, days=1)` by loading the destination via `get_by_id` and raising `DestinationNotFoundError` when it is missing. An omitted day count MUST be treated as 1. A day count below 1 MUST be rejected before scoring.

When `READINESS_V2_ENABLED` is false, the service MUST score with the P2 `compute_readiness` function and the destination's denormalized counters, using the same search-availability input the service uses today. It MUST NOT load place rows for that score. With that flag false, `search_available=False`, and zero enrichment and index counts, `place_count >= 100` MUST yield `score == 0.4` and `tier == "limited"`. `place_count >= 50` alone MUST NOT be treated as sufficient for a limited-band claim. The returned object MUST remain `DestinationReadinessOut` with the same fields as today.

When `READINESS_V2_ENABLED` is true, the service MUST load the destination's place rows, score them with the Readiness V2 rules for the requested day count, and return the same `DestinationReadinessOut` fields. `place_count` on that result MUST be the usable-place count from those rules. `enriched_pct` and `indexed_pct` MUST still come from the destination counters. The V2 path MUST NOT call Qdrant. A low V2 tier MUST NOT raise and MUST NOT turn an existing destination into a 404.

Missing destination MUST 404 on either flag value. An existing destination with zero enrichment MUST still return 200.

#### Scenario: Service readiness for existing unenriched destination

- **WHEN** `get_readiness` is called for a seeded destination with `place_count >= 100`, zero enriched and indexed counts, and `READINESS_V2_ENABLED` is false
- **THEN** the result has `tier == "limited"`, `enriched_pct == 0.0`, `indexed_pct == 0.0`, and `0.35 <= score <= 0.45`

#### Scenario: Service readiness for unknown destination

- **WHEN** `get_readiness` is called with a random UUID that does not exist
- **THEN** `DestinationNotFoundError` is raised

#### Scenario: Flag off ignores place geometry

- **WHEN** the flag is false and the destination counters would score limited, even if every stored place shares one coordinate
- **THEN** the tier and score match the P2 counter formula and the place rows are not read for scoring

## ADDED Requirements

### Requirement: Readiness V2 scores distribution for the requested days

When `READINESS_V2_ENABLED` is true, readiness MUST be a pure function of the place rows and the requested day count. It MUST NOT read the network, a database, or the clock. A place is usable only when its latitude is finite and inside -90..90, its longitude is finite and inside -180..180, the coordinate is not (0, 0), and it survives dedup. Dedup MUST collapse the same id, and MUST collapse the same case-folded name within 150 meters, to one place. Invalid coordinates MUST be excluded from the usable count.

The day count MUST be at least 1. The default thresholds MUST be 4 usable places per day, 3 distinct non-empty categories, and 2 clusters when the day count is greater than 1. Clusters MUST be single-linkage groups at 10 km. For a day count greater than 1, the spread check fails when there are fewer than 2 clusters or when the largest cluster holds more than 70 percent of the usable places. A share of exactly 70 percent MUST pass that part of the spread check. A day count of 1 MUST NOT apply the cluster check.

The coordinate check fails when any input place has invalid coordinates, including places that were excluded from the usable count. The share of usable places that have both a non-empty source and a retrieval timestamp MUST NOT change the tier by itself.

Tier and score MUST stay aligned with the existing bands. Usable count below 10 MUST be `sparse` with score below 0.3. Usable count of at least 10 with any failed count, category, spread, or coordinate check MUST be `limited` with score at least 0.3 and below 0.7. All of those checks passing MUST be `ready` with score at least 0.7 and a null message. `limited` and `sparse` MUST set a non-empty message that names the failed check. When the tier is not `ready` and the evidence share is below 1, that message MUST include the share. The function MUST NOT block trip generation.

#### Scenario: Ten clustered places are limited for three days

- **WHEN** ten usable places share one 10 km cluster, each has a valid coordinate, at least three categories are present, and the day count is 3
- **THEN** the tier is `limited`, the score is at least 0.3 and below 0.7, and the message names the place-count shortfall or the single cluster

#### Scenario: Twelve spread places are ready for three days

- **WHEN** twelve usable places form two clusters at least 10 km apart, neither cluster holds more than 70 percent, at least three categories are present, every coordinate is valid, and the day count is 3
- **THEN** the tier is `ready`, the score is at least 0.7, and the message is null

#### Scenario: Nine places are sparse

- **WHEN** nine places are usable and the day count is 1
- **THEN** the tier is `sparse` and the score is below 0.3

#### Scenario: One invalid coordinate blocks ready

- **WHEN** the other places would be ready for one day and one additional place has latitude 0 and longitude 0
- **THEN** the tier is not `ready` and the null-island place is not part of the usable count

#### Scenario: Same name within 150 meters counts once

- **WHEN** two places share a case-folded name and sit 100 meters apart, and no other places exist
- **THEN** the usable count is 1

#### Scenario: Evidence share does not change a ready tier

- **WHEN** every distribution check passes and one usable place has no source
- **THEN** the tier remains `ready` and the message remains null
