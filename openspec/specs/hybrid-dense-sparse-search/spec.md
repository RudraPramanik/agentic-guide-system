## Purpose

Hybrid dense + sparse (BM25-style) place retrieval with server-side RRF fusion on a dual Qdrant collection, including kill-switches and fail-soft degradation to dense-only or empty results without changing planner or HTTP contracts.

## Requirements

### Requirement: Sparse encoding is fail-soft and dependency-free
The system SHALL provide a sparse text encoder for places search that exposes availability and encode APIs. Encoding MUST use pure-Python tokenization and term weights with no new third-party packages. Encode failures MUST mark sparse unavailable (or return empty sparse vectors per batch contract) without raising into the request path. Query-side encoding without corpus IDF is acceptable for MVP.

#### Scenario: Sparse encode succeeds for place text
- **WHEN** sparse is available and encode is called with non-empty place or query text
- **THEN** a sparse vector suitable for Qdrant `bm25` named sparse vector is returned

#### Scenario: Sparse encode failure degrades availability
- **WHEN** sparse encoding raises or is otherwise unusable
- **THEN** sparse is treated as unavailable and callers continue without crashing the app

#### Scenario: No new package for default sparse path
- **WHEN** the default V5 sparse path is installed and imported
- **THEN** it does not require `rank-bm25`, `fastembed`, or other new requirements beyond existing project packages

### Requirement: Places collection uses a single settings-backed accessor
The system SHALL route ensure, upsert, search, and count_indexed collection names through one accessor (e.g. `places_collection()`) driven by `get_settings()`. Settings MUST include a V2 collection name (`QDRANT_PLACES_COLLECTION_V2`, default `places_v2`), `SEARCH_SPARSE_ENABLED`, and `SEARCH_RRF_K`. Misconfiguration MUST fail soft at ensure time and MUST NOT crash FastAPI boot.

#### Scenario: All index/search paths share one collection name
- **WHEN** ensure, upsert, search, and count run after settings load
- **THEN** each uses the same accessor result (no hard-coded split across modules)

#### Scenario: Boot with Qdrant down remains fail-soft
- **WHEN** ensure is called and Qdrant is unreachable
- **THEN** availability is False, the process continues, and search returns empty without raising

### Requirement: V2 collection supports named dense and sparse vectors
The system SHALL create (or ensure) the V2 places collection with a named dense vector (`dense`, cosine, size = `PLACES_EMBEDDING_DIM`) and a named sparse vector (`bm25`). The legacy unnamed `places` collection MUST NOT be mutated in place for hybrid schema. Empty or missing V2 before reindex MUST NOT cause HTTP 500s on search (empty → existing geo-fallback ladder in the planner).

#### Scenario: Ensure creates named-vector collection
- **WHEN** the V2 collection does not exist and Qdrant is available
- **THEN** ensure creates it with `dense` and `bm25` configs matching settings

#### Scenario: Legacy collection left intact during dual-collection phase
- **WHEN** V2 ensure/index runs while legacy `places` still exists
- **THEN** hybrid schema changes apply only to the V2 collection name from settings

### Requirement: Index upserts dense and sparse vectors when available
Indexing MUST upsert points with deterministic IDs `str(place.id)` and, when hybrid is enabled, named vectors `dense` and `bm25` derived from canonical text. Batch upsert MUST remain a single Qdrant upsert call per chunk. If dense embedding is empty, that point MUST be skipped (or not written as dense-only invisible incorrectly). Points with bm25-only when dense is missing are acceptable fail-soft and MAY be invisible under dense-only degradation.

#### Scenario: Batch hybrid upsert is one Qdrant call
- **WHEN** batch index runs for N eligible places with both encoders available
- **THEN** Qdrant upsert is awaited exactly once for that chunk with named vectors present

#### Scenario: Dense unavailable skips or omits dense for that point
- **WHEN** dense embedding fails for a place during index
- **THEN** the write path does not raise; the point is skipped or lacks a usable dense vector per documented fail-soft rules

### Requirement: Search uses hybrid RRF with dense-only degradation
`search_places` MUST remain destination-filtered and return `PlaceSearchResult`-compatible fields (`place_id`, `score`, optional `name` / `destination_id`). When sparse is enabled and available, search MUST prefetch dense and sparse and fuse with server-side RRF using configured `SEARCH_RRF_K`. When `SEARCH_SPARSE_ENABLED` is false or sparse is unavailable, search MUST use dense-only prefetch (behavior equivalent to pre-hybrid dense ranking for the same vectors). Qdrant or embedding failure MUST return `[]` without raising.

#### Scenario: Hybrid path returns destination-scoped results
- **WHEN** sparse is on/available and `search_places(query, destination_id=A, top_k=N)` runs successfully
- **THEN** results are filtered to destination A, length ≤ N, and include place_id + score

#### Scenario: Sparse kill-switch uses dense-only
- **WHEN** `SEARCH_SPARSE_ENABLED` is false (or sparse unavailable) and Qdrant is up
- **THEN** search uses dense-only prefetch and does not require sparse encode success

#### Scenario: Qdrant failure returns empty list
- **WHEN** the query path raises a Qdrant/network error after retries
- **THEN** `search_places` returns `[]` and does not raise

### Requirement: Cutover is harness-gated and reversible via env
Traffic MUST NOT flip to V2 until the target destinations are indexed and the golden harness passes against V2. Rollback MUST be possible by flipping the accessor/env and/or disabling sparse without schema migrations. Frontend and HTTP contracts MUST remain unchanged across cutover.

#### Scenario: Empty V2 is not used as live traffic
- **WHEN** V2 exists but has zero indexed points for a destination
- **THEN** operators MUST NOT flip the accessor to V2 for that traffic until index + harness validation succeed

#### Scenario: Rollback restores dense-healthy path
- **WHEN** operators set sparse off and/or point the accessor back to the validated collection
- **THEN** search remains healthy under tests without requiring a DB migration

#### Scenario: No frontend contract change
- **WHEN** hybrid cutover completes
- **THEN** HTTP paths, DTO envelopes, and SSE event names used by the frontend remain unchanged

### Requirement: Search MAY attach a fusion diagnostics sidecar
The hybrid or dense-only `search_places` path MUST continue to return destination-filtered `PlaceSearchResult`-compatible hits (or `[]` on failure) exactly as before for planning. When fusion diagnostics are enabled, the search layer MUST also make available a diagnostics sidecar describing mode and hit id orders. The sidecar MUST NOT reorder, filter, or replace the primary result list used by callers for candidate loading. Diagnostic subquery failures MUST be fail-soft and MUST NOT convert a successful primary result into `[]`.

#### Scenario: Primary hits unchanged when diagnostics present
- **WHEN** hybrid search succeeds and diagnostics are attached
- **THEN** the ordered place_id list used for planning matches the fused (or dense-only) primary query results, independent of diagnostic metadata

#### Scenario: Diagnostic error keeps primary results
- **WHEN** the primary query succeeds and a diagnostic subquery fails
- **THEN** `search_places` still returns the primary hits (not an empty list solely due to diagnostics)
