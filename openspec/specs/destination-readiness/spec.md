## Purpose

Destination readiness scoring — a pure `compute_readiness` function (no I/O) and its `DestinationService` wiring that turns denormalized destination counters into a `DestinationReadinessOut`.

## Requirements

### Requirement: Pure compute_readiness function

The system SHALL provide `compute_readiness(place_count, enriched_count, indexed_count, search_available) -> ReadinessResult` in `src/destinations/readiness.py` with `PLACE_TARGET = 100` and a frozen `ReadinessResult` dataclass (`score`, `tier`, `place_count`, `enriched_pct`, `indexed_pct`, `message`). The function MUST be pure (no SQLAlchemy, FastAPI, httpx, or qdrant imports) and MUST implement the locked P2 formula:

- `place_score = min(place_count / PLACE_TARGET, 1.0)`
- `enriched_pct = enriched_count / place_count if place_count > 0 else 0.0`
- `indexed_pct = (indexed_count / place_count) if (place_count > 0 and search_available) else 0.0`
- `score = round(0.4 * place_score + 0.35 * enriched_pct + 0.25 * indexed_pct, 3)`
- `tier = "ready" if score >= 0.7 else "limited" if score >= 0.3 else "sparse"`

Messages MUST be: sparse → `"Very limited POI data - results may be generic"`; limited when `enriched_pct < 0.5` → `"Limited enrichment - semantic search not yet available"`; ready → `None`.

#### Scenario: Unenriched Darjeeling-scale input is limited

- **WHEN** `compute_readiness(144, 0, 0, False)` is called
- **THEN** `tier == "limited"` and `0.35 <= score <= 0.45` and `enriched_pct == 0.0` and `indexed_pct == 0.0`

#### Scenario: Fully enriched and indexed input is ready

- **WHEN** `compute_readiness(144, 100, 100, True)` is called
- **THEN** `tier == "ready"` and `score >= 0.7` and `message is None`

#### Scenario: Zero places is sparse

- **WHEN** `compute_readiness(0, 0, 0, False)` is called
- **THEN** `tier == "sparse"` and score is below the limited threshold and the sparse message is set

### Requirement: DestinationService get_readiness uses compute_readiness

The system SHALL implement `DestinationService.get_readiness(destination_id)` by: (1) loading the destination via `get_by_id` (raising `DestinationNotFoundError` if missing); (2) setting `search_available=False` for P2; (3) calling `compute_readiness` with the destination’s denormalized counters; (4) returning `DestinationReadinessOut(destination_id=..., **result fields)`. The service MUST NOT call Qdrant. Missing destination MUST 404; existing destination with zero enrichment/index MUST still return 200 with computed score. Acceptance language for unenriched limited-band scoring MUST use a formula-true place-count floor: with `search_available=False` and zero enrichment/index, `place_count >= 100` yields `score == 0.4` / `tier == "limited"`; `place_count >= 50` alone MUST NOT be treated as sufficient for limited-band claims.

#### Scenario: Service readiness for existing unenriched destination

- **WHEN** `get_readiness` is called for a seeded destination with `place_count >= 100`, zero enriched/indexed
- **THEN** the result has `tier == "limited"`, `enriched_pct == 0.0`, `indexed_pct == 0.0`, and `0.35 <= score <= 0.45`

#### Scenario: Service readiness for unknown destination

- **WHEN** `get_readiness` is called with a random UUID that does not exist
- **THEN** `DestinationNotFoundError` is raised

### Requirement: Unenriched place_count floors are formula-true

Documentation and verification for unenriched P2 readiness (`search_available=False`, zero enriched/indexed) SHALL distinguish seed volume from readiness scoring. `place_count >= 50` MAY be used as a seed/Overpass volume floor. Limited-band and `score >= 0.35` claims MUST require `place_count >= 88` at minimum and SHOULD use `place_count >= 100` for the exact score `0.4`.

#### Scenario: Fifty places is sparse when unenriched

- **WHEN** `compute_readiness(50, 0, 0, False)` is evaluated
- **THEN** `score == 0.2` and `tier == "sparse"`
