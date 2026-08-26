## Purpose

P3 place knowledge layer: enriched_tags, Qdrant/embeddings search stack, enrich/index scripts, and readiness live availability.

## Requirements

### Requirement: Place enriched_tags column is distinct from raw OSM tags
The project SHALL add an additive `places.enriched_tags` JSONB column (list, NOT NULL, default empty list) without modifying the existing `places.tags` JSONB dict column.

Enrichment MUST persist LLM category tags only to `enriched_tags` and MUST NEVER write to `tags`.

#### Scenario: Both columns exist and remain distinct
- **WHEN** the `enriched_tags` migration has been applied
- **THEN** `Place` has both `tags` and `enriched_tags` columns, and enrichment update payloads include `enriched_tags` but not `tags`

#### Scenario: Empty enriched_tags after vocab filter is success
- **WHEN** the LLM returns only tags outside `PLACE_TAG_VOCAB` but a non-empty summary
- **THEN** enrichment persists `enriched_tags=[]` as success (not a skip/failure)

### Requirement: Qdrant places collection is created fail-soft via AsyncQdrantClient
The project SHALL provide `src/search/client.py` with a cached `get_qdrant_client()` returning `AsyncQdrantClient`, `ensure_places_collection()`, `is_qdrant_available()`, and `close_qdrant_client()`.

`ensure_places_collection()` MUST:
- Create (or ensure) the configured places collection with cosine distance and configured vector size.
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

### Requirement: Embedding abstraction is lifespan-loaded, thread-offloaded, and degrades gracefully
The project SHALL provide `src/search/embeddings.py` with `ensure_embedding_model_loaded()`, `is_embeddings_available()`, `embed_text(text)`, and `embed_batch(texts)`.

The embedding module MUST:
- Initialize from lifespan via `ensure_embedding_model_loaded()` (bounded timeout where applicable, fail-soft) — NOT implicitly at import time.
- Select behavior from `PLACES_EMBEDDING_BACKEND`:
  - `hosted`: call `src/core/llm/client.py` embedding helpers; no local SentenceTransformer.
  - `local`: load SentenceTransformer and offload every `encode(...)` with `asyncio.to_thread(...)`.
- If unavailable: `embed_text` returns `[]`; `embed_batch` returns `[[] for _ in texts]` (parallel-array contract, never a bare `[]`).
- Successful vectors MUST have length equal to `get_settings().PLACES_EMBEDDING_DIM` (production hosted Gemini typically 768).

Qdrant collection creation MUST continue to use `PLACES_EMBEDDING_DIM` from settings so hosted cutover recreates/indexes at the new size.

#### Scenario: Successful embed returns configured dim
- **WHEN** `embed_text("sunrise photography")` is called and embeddings are available
- **THEN** it returns a list of floats with length equal to `PLACES_EMBEDDING_DIM`

#### Scenario: Unavailable preserves batch shape
- **WHEN** embeddings are unavailable and `embed_batch(["a", "b"])` is called
- **THEN** the result equals `[[], []]` and does not raise

#### Scenario: Local encode does not block the event loop
- **WHEN** backend is `local` and `embed_text` runs concurrently with another coroutine while encode is slow
- **THEN** the other coroutine can make progress (encode is offloaded via `to_thread`)

#### Scenario: Hosted path does not require MiniLM
- **WHEN** `PLACES_EMBEDDING_BACKEND=hosted` during lifespan
- **THEN** embeddings may become available without constructing SentenceTransformer

### Requirement: LLM-based place enrichment is re-runnable with distinct failure modes
The project SHALL extend `PlaceService` with `_call_llm_and_parse(place)` and `enrich_place(place)`.

`enrich_place(place)` MUST:
- Skip when `place.summary` is already set (no LLM call).
- Call LLM only through `src/core/llm/client.py`.
- Persist `summary` and `enriched_tags` only (never `tags`).
- Filter tags to `PLACE_TAG_VOCAB` from `src/places/constants.py` (not Settings).
- On `WandrLLMError`: log under an LLM-failure code, return `None`, no DB write.
- On malformed/non-JSON/schema-invalid output: log under `enrichment.malformed_response`, return `None`, no DB write.

#### Scenario: Already enriched place is skipped
- **WHEN** `enrich_place()` is called for a `Place` with `summary != None`
- **THEN** it returns a skip result and does not call the LLM

#### Scenario: LLM call failure is contained
- **WHEN** the LLM call raises `WandrLLMError`
- **THEN** enrichment returns `None` and does not attempt a repository update

#### Scenario: Malformed LLM output is contained distinctly
- **WHEN** the LLM returns non-JSON or JSON missing a usable `summary`
- **THEN** enrichment returns `None`, does not write to the DB, and logs a malformed-response failure (distinct from `WandrLLMError`)

#### Scenario: Unknown tags are removed
- **WHEN** the LLM returns tags that are not in the controlled vocabulary
- **THEN** the persisted `enriched_tags` contain only allowed vocab entries

### Requirement: Qdrant indexing and semantic search are destination-scoped and batch-capable
The project SHALL provide `src/search/places_index.py` with `upsert_place`, `upsert_places_batch`, `search_places`, and `count_indexed`.

These functions MUST:
- Use deterministic point IDs `str(place.id)`.
- Derive embed text from `summary` and `enriched_tags` only (never raw `tags`).
- Filter search by payload `destination_id`.
- Check availability via `is_qdrant_available()` (function).
- Degrade to `[]` / no-op without raising on Qdrant or embedding failures.
- `upsert_places_batch` MUST issue one Qdrant upsert per chunk (not N) and use `embed_batch`.
- `count_indexed` MUST return Qdrant’s filtered count (ground truth), not a local run tally.

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
- **THEN** `search_places(...)` returns `[]` without calling embed or Qdrant search

### Requirement: Semantic search uses the Qdrant query-points path
`search_places` SHALL issue destination-scoped retrieval via the Qdrant client's query-points API (not the deprecated search API). Mapping from the query response to `PlaceSearchResult` MUST preserve `place_id`, `score`, and payload fields (`name`, `destination_id`) used by callers today. Fail-soft contracts from the existing indexing/search requirement remain in force: unavailable Qdrant or empty embedding short-circuits to `[]` without raising; Qdrant errors degrade to `[]`.

#### Scenario: Destination filter still applied
- **WHEN** `search_places(query, destination_id=A, top_k=N)` is invoked with Qdrant available and a non-empty embedding
- **THEN** the Qdrant query-points call includes a filter requiring payload `destination_id == A`

#### Scenario: Qdrant error returns empty list
- **WHEN** the query-points call raises
- **THEN** `search_places` returns `[]` and does not raise

#### Scenario: Empty embedding never calls Qdrant
- **WHEN** embedding returns an empty vector
- **THEN** `search_places` returns `[]` without calling query-points

#### Scenario: Pinned tests mock query-points
- **WHEN** the three search_places unit tests run
- **THEN** they assert against `query_points` (not the deprecated `search` method)

### Requirement: Enrichment and indexing scripts are batch re-runnable and counter-safe
The project SHALL provide `scripts/enrich_places.py` and `scripts/index_places.py` with session-injected helpers that do not open a session or commit.

Scripts MUST:
- Treat `limit=0` / non-positive as unlimited — MUST NEVER call `.limit(0)`.
- Wrap each enrichment DB write in `session.begin_nested()`.
- Run enrichment LLM calls concurrently under a configured semaphore; keep DB writes sequential on one session.
- Recompute `Destination.enriched_count` from DB truth (`summary IS NOT NULL`).
- Use `upsert_places_batch` for indexing chunks and set `Destination.indexed_count` from `count_indexed()`.
- On Qdrant/embeddings unavailable during index: degrade (warn), exit 0 — not a hard failure.

#### Scenario: One place DB write failure does not poison the batch
- **WHEN** one place’s persist raises mid-batch under a real DB session
- **THEN** subsequent places still succeed because of SAVEPOINT isolation

#### Scenario: limit=0 means unlimited
- **WHEN** enrich/index helpers are invoked with `limit=0`
- **THEN** the SQL statement has no `LIMIT 0` clause and eligible rows are not artificially emptied

#### Scenario: indexed_count uses Qdrant ground truth
- **WHEN** indexing runs with a `--limit` smaller than the true indexed set
- **THEN** persisted `Destination.indexed_count` equals `count_indexed(destination_id)`, not the run’s local success tally

### Requirement: Destination readiness uses live search availability
The project SHALL update `DestinationService.get_readiness()` to set `search_available = is_qdrant_available()` (one-way dependency). `src/search/` MUST NOT import `src/destinations/`.

`compute_readiness` itself MUST remain unchanged.

#### Scenario: Ready tier is reachable after P3
- **WHEN** Qdrant is available and enriched/indexed counts are high relative to place_count
- **THEN** readiness tier can be `ready` (no longer permanently capped at `limited`)

#### Scenario: Qdrant down degrades indexed component
- **WHEN** `is_qdrant_available()` is False even if DB `indexed_count` is high
- **THEN** readiness returns 200 with `indexed_pct == 0.0` (the indexed DB counter does not contribute to the score)

Note: under the locked P2 formula, place+enriched alone can still yield `tier=ready` (score ≥ 0.7) without the indexed term. Tests that also assert a non-ready tier on Qdrant-down MUST use a gated fixture where place+enriched alone stay below 0.7.

#### Scenario: Gated fixture proves live flag controls tier
- **WHEN** place+enriched alone score below 0.7, indexed counts are high enough that with search available the tier would be `ready`, and `is_qdrant_available()` is False
- **THEN** readiness returns `indexed_pct == 0.0` and tier is `limited` or `sparse`
