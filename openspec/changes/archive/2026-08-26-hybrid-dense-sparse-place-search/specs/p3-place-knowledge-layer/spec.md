## MODIFIED Requirements

### Requirement: Qdrant indexing and semantic search are destination-scoped and batch-capable
The project SHALL provide `src/search/places_index.py` with `upsert_place`, `upsert_places_batch`, `search_places`, and `count_indexed`.

These functions MUST:
- Use deterministic point IDs `str(place.id)`.
- Derive embed/sparse text from `summary`, `enriched_tags`, and place `name` (optionally `category`) — never raw OSM `tags`. Empty `name` MUST be omitted gracefully.
- Address the Qdrant collection only via the single settings-backed places collection accessor (not ad-hoc string literals split across call sites).
- Filter search by payload `destination_id`.
- Check availability via `is_qdrant_available()` (function).
- Degrade to `[]` / no-op without raising on Qdrant or embedding failures.
- `upsert_places_batch` MUST issue one Qdrant upsert per chunk (not N) and use batch embedding (and sparse batch encode when hybrid is active).
- `count_indexed` MUST return Qdrant’s filtered count (ground truth), not a local run tally.
- When hybrid search is configured and sparse is available, search MAY fuse dense and sparse rankings via server-side RRF while preserving the `PlaceSearchResult` field contract consumed by planner tools.

#### Scenario: Indexing is idempotent by point id
- **WHEN** `upsert_place()` is called twice for the same `Place`
- **THEN** upsert uses the same point id both times

#### Scenario: Batch upsert is a single Qdrant call
- **WHEN** `upsert_places_batch` is called with N eligible places
- **THEN** the Qdrant client upsert is awaited exactly once for that chunk

#### Scenario: Search is filtered to a destination
- **WHEN** `search_places(query, destination_id=A, top_k=N)` is called
- **THEN** results are filtered to payload `destination_id == A`

#### Scenario: Unavailable Qdrant short-circuits before embed
- **WHEN** `is_qdrant_available()` is False
- **THEN** `search_places` returns `[]` without calling the embedding backend

#### Scenario: Canonical text includes place name tokens
- **WHEN** a place with non-empty `name` (and optional `category`) is indexed
- **THEN** the text used for dense (and sparse, when hybrid) encoding includes those name tokens in addition to `summary` and `enriched_tags`

#### Scenario: Empty name is omitted without failing index
- **WHEN** a place has empty/null `name` but non-empty `summary`
- **THEN** indexing proceeds using summary and enriched_tags without raising

### Requirement: Qdrant places collection is created fail-soft via AsyncQdrantClient
The project SHALL provide `src/search/client.py` with a cached `get_qdrant_client()` returning `AsyncQdrantClient`, `ensure_places_collection()`, `is_qdrant_available()`, and `close_qdrant_client()`.

`ensure_places_collection()` MUST:
- Create (or ensure) the configured places collection via the single places collection accessor.
- When the configured collection is the hybrid V2 collection, use named dense + sparse vector configs (cosine dense sized to `PLACES_EMBEDDING_DIM`, plus sparse `bm25`).
- When the configured collection is legacy dense-only, preserve cosine dense vector creation sized to `PLACES_EMBEDDING_DIM`.
- Bound awaits with `asyncio.wait_for` using configured timeout.
- Never raise during FastAPI lifespan startup. On failure after retries: log warning, set availability False, allow app start.
- Expose availability only via `is_qdrant_available()` — callers MUST NOT import a raw module-level boolean by value.

Default availability MUST be False until a successful ensure.

#### Scenario: Qdrant unreachable at startup degrades search
- **WHEN** `ensure_places_collection()` is called and the ensure path raises a connection-related error
- **THEN** the function catches the error, `is_qdrant_available()` is False, and subsequent `search_places(...)` calls return `[]` without raising

#### Scenario: Availability is live across modules
- **WHEN** availability is flipped via the client module setter/ensure path
- **THEN** another module that calls `is_qdrant_available()` observes the new value immediately (not a stale imported copy)

#### Scenario: Hybrid V2 ensure uses named vectors
- **WHEN** the places collection accessor resolves to the V2 hybrid collection and the collection is missing
- **THEN** ensure creates it with named `dense` and sparse `bm25` configuration without mutating the legacy dense-only collection schema in place
