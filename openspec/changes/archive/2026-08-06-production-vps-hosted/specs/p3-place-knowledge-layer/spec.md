## MODIFIED Requirements

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
