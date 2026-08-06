## Purpose

Hosted place embeddings via LiteLLM through `src/core/llm/client.py`, with optional local MiniLM for development.

## Requirements

### Requirement: Hosted embeddings go through the LLM gateway
The system SHALL expose embedding calls for place search exclusively through `src/core/llm/client.py` (LiteLLM). `src/search/embeddings.py` MUST NOT import `litellm` or provider SDKs directly.

When `PLACES_EMBEDDING_BACKEND=hosted`, `embed_text` / `embed_batch` MUST call the gateway using `PLACES_EMBEDDING_MODEL` (prod default Gemini via LiteLLM id such as `gemini/text-embedding-004`) and MUST return vectors whose length equals `PLACES_EMBEDDING_DIM`.

#### Scenario: Hosted embed succeeds with configured dim
- **WHEN** backend is `hosted`, embeddings are available, and `embed_text("quiet cafes")` succeeds
- **THEN** the result is a float list with length `PLACES_EMBEDDING_DIM`

#### Scenario: Search module does not import litellm
- **WHEN** `src/search/embeddings.py` is inspected
- **THEN** it has no `litellm` import and depends on `core/llm` for hosted calls

### Requirement: Hosted embedding failures stay fail-soft
Hosted embedding HTTP/API failures MUST use explicit timeouts and retries consistent with the LLM client resilience style. After final failure, `embed_text` MUST return `[]` and `embed_batch` MUST return one empty list per input (parallel-array contract) without raising to callers.

#### Scenario: Provider outage preserves batch shape
- **WHEN** the hosted embedding API fails after retries during `embed_batch(["a", "b"])`
- **THEN** the result equals `[[], []]` and no exception escapes `embed_batch`

### Requirement: Lifespan does not load MiniLM for hosted backend
When `PLACES_EMBEDDING_BACKEND=hosted`, `ensure_embedding_model_loaded()` MUST NOT construct a `SentenceTransformer`. It MAY perform a lightweight availability check and MUST set `is_embeddings_available()` accordingly (fail-soft on check failure).

#### Scenario: Hosted startup skips SentenceTransformer
- **WHEN** the app lifespan runs with `PLACES_EMBEDDING_BACKEND=hosted`
- **THEN** no local SentenceTransformer model load is attempted

### Requirement: Local MiniLM remains optional for development
When `PLACES_EMBEDDING_BACKEND=local`, the existing MiniLM lifespan-load + `to_thread(encode)` behavior MUST remain available for development/tests. Production documentation and the production image MUST default to / assume `hosted`.

#### Scenario: Local backend still offloads encode
- **WHEN** backend is `local`, the model loaded, and `embed_text` runs
- **THEN** encode is offloaded via `asyncio.to_thread` as before

### Requirement: Embedding abstraction is lifespan-loaded, thread-offloaded, and degrades gracefully
The project SHALL provide `src/search/embeddings.py` with `ensure_embedding_model_loaded()`, `is_embeddings_available()`, `embed_text(text)`, and `embed_batch(texts)`.

The embedding module MUST:
- Initialize from lifespan via `ensure_embedding_model_loaded()` (bounded timeout where applicable, fail-soft) — NOT implicitly at import time.
- Select behavior from `PLACES_EMBEDDING_BACKEND`:
  - `hosted`: call `src/core/llm/client.py` embedding helpers; no local SentenceTransformer.
  - `local`: load SentenceTransformer and offload every `encode(...)` with `asyncio.to_thread(...)`.
- If unavailable: `embed_text` returns `[]`; `embed_batch` returns `[[] for _ in texts]` (parallel-array contract, never a bare `[]`).
- Successful vectors MUST have length equal to `get_settings().PLACES_EMBEDDING_DIM` (prod Gemini path typically `768`, not MiniLM `384`).

#### Scenario: Successful model load returns a vector
- **WHEN** `embed_text("sunrise photography")` is called and embeddings are available
- **THEN** it returns a list of floats with length equal to `PLACES_EMBEDDING_DIM`

#### Scenario: Model unavailable preserves batch shape
- **WHEN** embeddings are unavailable and `embed_batch(["a", "b"])` is called
- **THEN** the result equals `[[], []]` and does not raise

#### Scenario: Local encode does not block the event loop
- **WHEN** backend is `local` and `embed_text` runs concurrently with another coroutine while encode is slow
- **THEN** the other coroutine can make progress (encode is offloaded via `to_thread`)

#### Scenario: Hosted backend uses configured dim not MiniLM 384
- **WHEN** backend is `hosted` with `PLACES_EMBEDDING_DIM=768` and embed succeeds
- **THEN** the returned vector length is 768
