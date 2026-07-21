## ADDED Requirements

### Requirement: Readiness scoring function

The system SHALL compute a 0.0–1.0 readiness score in `src/destinations/readiness.py` from place count, enriched percentage, and indexed percentage with tiers: ready ≥0.7, limited ≥0.3, sparse <0.3.

#### Scenario: Seeded enriched destination

- **WHEN** a destination has ≥100 places mostly enriched and indexed
- **THEN** tier is `ready` and score ≥ 0.7

### Requirement: Readiness endpoint

The system SHALL expose `GET /api/v1/destinations/{id}/readiness` returning `ApiResponse[DestinationReadinessOut]`.

#### Scenario: Qdrant unavailable

- **WHEN** Qdrant is unreachable
- **THEN** `indexed_pct=0`, score still computed, endpoint returns 200
