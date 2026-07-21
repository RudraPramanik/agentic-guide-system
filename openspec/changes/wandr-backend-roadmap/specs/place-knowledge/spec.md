## ADDED Requirements

### Requirement: Qdrant collection bootstrap

The system SHALL ensure a `places` vector collection (384-d cosine) at app lifespan via `src/search/client.py`. Unreachable Qdrant SHALL set `search_available=False` without crashing startup.

#### Scenario: Local Qdrant healthy

- **WHEN** app starts with Qdrant on localhost:6335
- **THEN** log indicates collection ready

### Requirement: Text embeddings

The system SHALL embed place text via `src/search/embeddings.py` using `all-MiniLM-L6-v2`. Model load failure SHALL degrade to empty embeddings.

#### Scenario: Embed query text

- **WHEN** `embed_text("photography sunrise")` succeeds
- **THEN** a 384-dimensional float vector is returned

### Requirement: Place enrichment

The system SHALL enrich places via LLM JSON mode in `places/service.py`, skipping already-enriched rows.

#### Scenario: Enrich one place

- **WHEN** `enrich_place` is called on a place without summary
- **THEN** summary and controlled-vocab tags are persisted

### Requirement: Semantic place search

The system SHALL search places via `src/search/places_index.py` with PostGIS radius fallback on Qdrant failure.

#### Scenario: Semantic search ranking

- **WHEN** `search_places("photography sunrise", destination_id, 10)` runs on indexed Darjeeling
- **THEN** viewpoint/photography places rank highly

### Requirement: Batch enrich and index scripts

The system SHALL provide `scripts/enrich_places.py` and `scripts/index_places.py` re-runnable per destination.

#### Scenario: Full index pipeline

- **WHEN** enrich then index scripts finish for Darjeeling
- **THEN** Qdrant contains vectors for all enriched places
