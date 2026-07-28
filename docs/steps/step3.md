# Wandr — P3 Cursor Prompts: Place Knowledge Layer (v2 — hardened)
> Blueprint: [`docs/blueprint_final.md`](../blueprint_final.md) — Phase P3 (3 days · 5 steps, expanded to 7 + testing/checklist)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **v2 changelog:** fixes a schema-breaking type mismatch, two cross-module stale-flag bugs (one
> baked into the v1 tests themselves), a blocking-call-in-async bug, an SQL `LIMIT 0` gotcha, a
> missing Postgres transaction-poisoning guard, and closes the P2→P3 readiness-tier gap. See the
> Fix Log below before implementing anything.
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance until the current
> ✅ validation passes.

## v2 Fix Log (read this before implementing)

| # | Issue in v1 | Fix in v2 |
|---|---|---|
| 1 | `enrich_place()` overwrites `Place.tags` (a `JSONB dict` of raw OSM tags from P2) with a `list[str]` of LLM category tags — wrong type, destroys the original OSM tag data | New column `Place.enriched_tags: list[str]` (migration in new **Step 3.0**). Raw `tags` is never touched by enrichment. |
| 2 | `search_available` designed as a raw module-level `bool`, imported by value (`from src.search.client import search_available`) into `places_index.py` — the imported copy never reflects later changes in `client.py`. The v1 test suite patches the *stale local copy*, so tests pass while validating broken runtime behavior | Replaced with `is_qdrant_available()` / `is_embeddings_available()` functions that always read live module state. Same fix applied to the embeddings-availability flag. |
| 3 | `get_qdrant_client()` implied a sync `QdrantClient`, then wrapped calls in `asyncio.wait_for(...)` — wrapping a blocking sync call in `wait_for` does not stop it blocking the event loop | Locked to `qdrant_client.AsyncQdrantClient`. `wait_for` now actually bounds a real coroutine. |
| 4 | `embed_text()`/`embed_batch()` call `SentenceTransformer.encode()` directly inside `async def` — CPU-bound, blocks the event loop on every call, including live query-time semantic search | Wrapped in `asyncio.to_thread(...)`. |
| 5 | `embed_batch()`'s empty-result contract left as "return `[]` OR list of empty lists — choose one" | Locked: `[[] for _ in texts]` — a parallel array, so callers can `zip(inputs, outputs)` without guessing. |
| 6 | Model loading described as happening automatically at module import time, with no bound on a hung/slow download | Explicit `ensure_embedding_model_loaded()` called from lifespan (sibling of `ensure_places_collection()`), wrapped in `asyncio.wait_for(..., PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS)`, fail-soft. |
| 7 | `--limit 0` fed straight into `.limit(0)` — in SQL this returns **zero rows**, not "unlimited." A script would silently process nothing and report success | Locked: `if limit and limit > 0: stmt = stmt.limit(limit)` — `.limit()` is never called with `0`. |
| 8 | `enrich_places.py`'s per-place loop had no isolation for genuine DB write failures — a single flush failure inside a shared session poisons the whole Postgres transaction (asyncpg: "current transaction is aborted") until rollback, silently failing every subsequent place in the batch | Locked: `session.begin_nested()` (SAVEPOINT) around each per-place write, with a regression test proving this specifically (not just "we caught the exception"). (P2 `seed_destination.py` already uses `begin_nested()` — no backport needed.) |
| 9 | `index_places.py` sets `Destination.indexed_count` from "this run's success tally" — wrong after any `--limit`-bounded or partial run, since it doesn't reflect total indexed state | New `count_indexed(destination_id)` queries Qdrant's own count as ground truth (mirrors `enrich_places.py`'s existing correct pattern of recomputing `enriched_count` from DB truth). |
| 10 | `embed_batch()` was specified but never called anywhere — dead code, and a missed real batching win (sentence-transformers batches efficiently; Qdrant supports batch upsert) | New `upsert_places_batch()` uses `embed_batch()` + a single Qdrant batch upsert call per chunk. `index_places.py` now uses this instead of N sequential single-item upserts. |
| 11 | No handling for malformed/non-JSON LLM enrichment output — only `WandrLLMError` (call failure) was handled, not parse/schema failures (empty summary, missing keys, invalid JSON) | Explicit `try/except (json.JSONDecodeError, KeyError, ValueError, TypeError)` path, logged under a distinct code, returns `None` without persisting. |
| 12 | `PLACE_TAG_VOCAB` was to be added to `Settings`/`.env` — but it's a fixed domain rule, not a deployment concern, inconsistent with the blueprint's own `travel_rules.py` precedent for "constants are data, not env config" | Moved to `src/places/constants.py`, a plain constants module (sibling pattern to `travel_engine/travel_rules.py`). |
| 13 | `enrich_places.py` enriches strictly sequentially — one LLM call at a time. At ~150 places/destination and multi-second LLM latency, that's 10–15 minutes per destination with no parallelism | LLM calls (the slow, network-bound part) now run concurrently under a bounded `asyncio.Semaphore`; DB writes (must stay serialized on one session) remain sequential with per-item `begin_nested()`. Network-bound work parallelized, DB-write correctness unchanged. |
| 14 | P2 explicitly stated readiness `tier=ready` requires P3 enrichment/indexing — but no P3 step ever updates `DestinationService.get_readiness()`, which still hardcodes `search_available=False` forever | New **Step 3.6** wires `is_qdrant_available()` into readiness, closing the loop the blueprint itself promised. |

---

## Prerequisites (P2 must be complete)

Before step 3.0, confirm P2 from `docs/context.md`:

- All P2 steps ✅ — geo/places/destinations verified with pytest + `scripts/test_p2_smoke.py`
- Postgres DB reachable for async SQLAlchemy and PostGIS works (radius queries correct, using the locked `::geography` cast)
- Seeded test destination exists in dev DB (Darjeeling by default)
- `DestinationService.get_readiness()` currently hardcodes `search_available=False` — this is expected and will be fixed in Step 3.6, not before.
- `docker-compose.yml`'s Qdrant service is running (`qdrant/qdrant:latest`, host port **6335** → container 6333)
- Current stubs exist (do NOT assume any P3 implementation):
  - `src/search/client.py` (stub)
  - `src/search/embeddings.py` (stub)
  - `src/search/places_index.py` (stub)
  - `scripts/enrich_places.py` (stub)
  - `scripts/index_places.py` (stub)
  - `src/places/service.py` currently supports only list/get; it must be extended for enrichment

## Prompt conventions (every step)

- **Extend, don't replace** P2 code unless the step explicitly says replace.
- **Availability flags are functions, never raw importable booleans (v2 rule).** Any module that needs to know whether Qdrant or the embedding model is available calls `is_qdrant_available()` / `is_embeddings_available()` — it never does `from src.search.client import search_available`-style imports of a mutable value.
- **CPU-bound or blocking calls inside `async def` MUST be wrapped in `asyncio.to_thread(...)` (v2 rule).** This applies to every `SentenceTransformer.encode()` call.
- **Batch loops that write to a shared DB session per item MUST wrap each item's write in `session.begin_nested()` (v2 rule).** A bare try/except around a `flush()` is not sufficient — Postgres poisons the whole transaction on a genuine DB error until rollback.
- **Never call `.limit(0)` (v2 rule).** `0` and "no limit" are different concepts; guard explicitly.
- **Failure boundaries:** any external I/O must have an explicit typed fallback:
  - Qdrant unreachable or embeddings unavailable → semantic search returns `[]` (never 500)
  - LLM enrichment call error (`WandrLLMError`) → skip that place and continue batch
  - LLM enrichment *parse* error (malformed JSON/schema) → skip that place and continue batch (distinct failure mode from the above, v2 addition)
- **Time:** use `datetime.now(timezone.utc)` when writing timestamps.
- **External I/O:** LLM calls must go through `src/core/llm/client.py` only. Qdrant calls only through `src/search/client.py` and `src/search/places_index.py`. `sentence_transformers` imports only in `src/search/embeddings.py`.
- **Windows:** use `Select-String` instead of `grep` where noted in validation.
- **No new packages without requirements.txt + why-comment.**

## P3 architecture (read before implementing)

Canonical build order (the only order stated/locked in this doc):

```
3.0 migration: Place.enriched_tags column
  -> 3.1 qdrant async client + collection ensure
    -> 3.2 embeddings abstraction (thread-offloaded, explicit load step)
      -> 3.3 enrich_place() in PlaceService (LLM+parse split, malformed-JSON handling)
        -> 3.4 places_index (single + batch upsert, semantic search, ground-truth count)
          -> 3.5 enrich/index scripts (bounded concurrency, savepoints, limit(0) guard)
            -> 3.6 wire readiness endpoint to real search availability (closes P2→P3 gap)
```

Layer rules (non-negotiable):

- Router → Service → Repository only (routers unchanged in P3).
- LLM only through `src/core/llm/client.py`.
- Geo only through `src/geo/` (P3 does not add geo/network calls).
- `travel_engine/` remains pure Python and unused in P3.
- **New (v2):** `destinations/service.py` may read `search/client.py`'s availability status (one-way dependency, status-check only). `search/` must never import from `destinations/` — keep the dependency graph acyclic.

## P3 design decisions (locked)

### Schema: raw tags vs. enriched tags (v2 locked)

`Place.tags` (JSONB dict, raw OSM tags from Overpass) and `Place.enriched_tags` (JSONB list, LLM-derived controlled-vocab tags) are **separate columns with separate owners**:

| Column | Type | Written by | Never touched by |
|---|---|---|---|
| `tags` | `dict` | P2 seed script (Overpass) | Enrichment, forever |
| `enriched_tags` | `list[str]` | P3 enrichment (`enrich_place`) | Seed script, forever |

### Qdrant identity and payload schema

- `point_id = str(place.id)` — a `uuid.UUID`'s `str()` form is a valid Qdrant point ID (Qdrant accepts UUID-format strings or unsigned ints).
- Qdrant payload MUST include: `destination_id` (stringified UUID), `place_id` (stringified UUID; explicit redundancy for debugging/tests), optional metadata: `name`, `osm_id`, `category`.

### Destination-scoped search filter

- `search_places(query, destination_id, top_k)` MUST filter by `destination_id`. Unfiltered search would let trip planning silently draw places from the wrong city — forbidden.

### Async Qdrant client — LOCKED (v2)

Use `qdrant_client.AsyncQdrantClient`, never the sync `QdrantClient`. Wrapping a sync blocking call in `asyncio.wait_for` does not preempt it — the event loop stays blocked for the call's full duration regardless of the timeout. Only a real coroutine can be meaningfully bounded and cancelled this way.

### Availability flags are functions, not raw booleans — LOCKED (v2)

`src/search/client.py` exposes `is_qdrant_available() -> bool`. `src/search/embeddings.py` exposes `is_embeddings_available() -> bool`. Nothing outside these two modules ever does `from ... import <bool name>` — Python binds imported names to the value at import time, so a later flip of the underlying flag is invisible to anything that imported it by value. This is not a style preference; it is the difference between working and silently-broken degradation logic.

### Embedding batch contract — LOCKED (v2)

`embed_batch(texts) -> list[list[float]]` always returns one entry per input text, in order. When embeddings are unavailable: `[[] for _ in texts]`, never a bare `[]`. Callers `zip(texts, vectors)` and skip any pair where the vector is empty.

### CPU-bound calls in async code — LOCKED (v2)

Every `SentenceTransformer.encode(...)` call — single or batch — is wrapped in `await asyncio.to_thread(model.encode, ...)`. Without this, a query-time semantic search call blocks the entire event loop (and every concurrent request being served) for the duration of inference.

### Model loading is an explicit, bounded lifespan step — LOCKED (v2)

Model loading does NOT happen implicitly at module import time. `ensure_embedding_model_loaded()` is called from `main.py`'s lifespan, alongside `ensure_places_collection()`, wrapped in `asyncio.wait_for(..., PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS)`. This bounds a hung download, matches the sibling `ensure_*` pattern already established for Qdrant, and makes the side effect explicit rather than "importing a module happens to trigger a multi-second download."

**Production note:** on resource-constrained hosts (e.g. an ARM VPS), pre-bake the model into the Docker image at build time (`SENTENCE_TRANSFORMERS_HOME` cache dir committed to the image layer) so production never attempts a runtime download at all. Document this in the deploy runbook — it's a real operational risk, not just a nice-to-have.

### Controlled tag vocabulary lives in a constants module, not `Settings` — LOCKED (v2)

`PLACE_TAG_VOCAB` is a fixed domain/business rule, not a per-deployment config value — it does not belong in `Settings`/`.env`. It lives in `src/places/constants.py`, mirroring the blueprint's own precedent of `travel_engine/travel_rules.py` for domain constants:

```
offbeat, photography, viewpoint, trek, monastery, cultural, family, nature, adventure
```

Tags produced by the LLM MUST be filtered to a strict subset of this vocab. Unknown tags are discarded, not mapped. An empty `enriched_tags` list after filtering is a **valid, persisted outcome** (some POIs won't match any interest category) — it is not treated as an enrichment failure. Only a missing/empty `summary` is a hard validation failure.

**Forward-compat note:** P4's `travel_engine/travel_rules.py` will define `CATEGORY_WEIGHTS` over a subset of these tags — when building P4, confirm every `CATEGORY_WEIGHTS` key exists in `PLACE_TAG_VOCAB`, or `place_selector.py` will silently score unrecognized tags at a default weight.

### Enrichment failure modes — LOCKED (v2, two distinct modes, not one)

| Failure | Detected by | Handling |
|---|---|---|
| LLM call itself fails (timeout, rate limit exhausted) | `WandrLLMError` raised by `chat_completion` | Log, return `None`, batch continues |
| LLM responded, but output is malformed (invalid JSON, missing `summary` key, empty summary string) | `try/except (json.JSONDecodeError, KeyError, ValueError, TypeError)` around parsing | Log under a distinct code (`enrichment.malformed_response`), return `None`, batch continues |

Both are "place skipped, re-runnable later" — neither aborts the batch, and neither is conflated with the other in logs (you need to be able to tell "the LLM was down" apart from "the LLM is returning garbage for this prompt").

### Batch DB writes require per-item transaction isolation — LOCKED (v2)

Any loop that performs a per-item DB write inside one shared `AsyncSession` MUST wrap each item's write in `session.begin_nested()` (a SAVEPOINT):

```python
for item in batch:
    try:
        async with session.begin_nested():
            await repo.update(item.id, {...})
    except Exception as e:
        log.warning("batch.item_failed", item_id=str(item.id), error=str(e))
        continue
```

Without this, a genuine DB-level failure on one item (not just an app-level "expected" failure) leaves the underlying Postgres transaction in an aborted state — every subsequent statement in the same transaction fails with "current transaction is aborted, commands ignored until end of transaction block," silently wiping out the rest of the batch even though the code *looks* like it's continuing. A bare `try/except` around a `flush()` does not protect against this; only an explicit SAVEPOINT does.

**Note:** P2's `scripts/seed_destination.py` already wraps per-POI writes in `session.begin_nested()` — no follow-up needed there.

### Ground-truth counters, not last-run tallies — LOCKED (v2)

`Destination.enriched_count` is recomputed from a DB count query after every enrichment run (v1 already did this correctly). `Destination.indexed_count` must follow the same principle: recomputed from Qdrant's own `count()` API filtered by `destination_id`, not from "how many succeeded in this particular run." A `--limit`-bounded or partially-failed run must never leave `indexed_count` understating (or overstating) the true indexed state.

### Config additions (step 3.1 / 3.2)

Add to `src/config.py` and `.env.example`:

```python
QDRANT_URL: str = "http://localhost:6335"  # host port; compose maps 6335:6333
QDRANT_API_KEY: str = ""
QDRANT_PLACES_COLLECTION: str = "places"
PLACES_EMBEDDING_DIM: int = 384
QDRANT_OPERATION_TIMEOUT_SECONDS: float = 5.0
QDRANT_OPERATION_MAX_RETRIES: int = 2          # documentation of the contract; retry decorators
                                                # use a matching literal, same convention as
                                                # core/llm/client.py's LLM_MAX_RETRIES
PLACES_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS: float = 30.0
ENRICH_BATCH_LLM_CONCURRENCY: int = 3           # bounded concurrent LLM calls during enrichment
```

**Implement note (do not skip):** `src/config.py` already has `QDRANT_URL` / `QDRANT_API_KEY`
from earlier scaffolding with a wrong host default (`http://localhost:6333`). Step 3.1 MUST
change that default to `http://localhost:6335` so bare Settings (no `.env`) match compose.
`.env.example` already uses `6335` — keep it aligned. Do not invent a second URL setting.

---

## Step 3.0 — Migration: Place.enriched_tags column ★ NEW (v2)

```
Read AGENT.md before proceeding.

TASK: Add the Place.enriched_tags column that P3 enrichment writes to. This MUST land before
step 3.3 — enrichment must never write LLM-derived tags into the existing raw-OSM `tags` column.
This is step 3.0. No package installs.

─── UPDATE src/places/models.py ───

Add one column to the existing Place model (do not touch the existing `tags` column):

  from sqlalchemy.dialects.postgresql import JSONB

  class Place(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
      # ... existing columns unchanged ...
      enriched_tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

─── GENERATE AND REVIEW MIGRATION ───

  alembic revision --autogenerate -m "add_place_enriched_tags"

Review the generated file before running:
  [ ] Only adds `enriched_tags` to `places` — touches no other table
  [ ] Column type is JSONB, default server-side or app-side empty list, NOT NULL
  [ ] Existing `tags` column is untouched

Run:
  alembic upgrade head

─── RULES ───
- `tags` (raw OSM dict) and `enriched_tags` (LLM-derived list) are permanently separate —
  see the locked P3 design decision above. No code in P3 ever assigns to `place.tags`.
- JSONB list column uses `default=list` (callable), never `default=[]`.

─── FAILURE BOUNDARY ───
Migration touches only additive schema — no backfill required (existing rows get `[]`).
Must NOT: rename or repurpose the existing `tags` column.

─── VALIDATION ───
  docker exec wandr_postgres psql -U wandr -d wandr -c "\d places"

Expected: `enriched_tags` column present, type jsonb, not null. `tags` column unchanged.

  python -c "
from src.places.models import Place
cols = {c.name for c in Place.__table__.columns}
assert 'tags' in cols and 'enriched_tags' in cols
print('PASS — both tag columns present and distinct')
"
```

---

## Step 3.1 — search/client.py — async Qdrant client + collection ensure

```
Read AGENT.md before proceeding.

TASK: Implement an ASYNC Qdrant client + idempotent "ensure collection" with fail-soft startup
behavior, exposed via a function-based availability check (not a raw boolean import).
This is step 3.1.

─── INSTALL ───
Append to requirements.txt:
  qdrant-client==1.15.1     # vector search for P3 semantic retrieval — AsyncQdrantClient used throughout

Install:
  pip install qdrant-client==1.15.1

─── IMPLEMENT src/search/client.py ───

  ⚠️ CORRECTNESS-CRITICAL (v2): use qdrant_client.AsyncQdrantClient, never the sync
  QdrantClient. Wrapping a sync blocking call in asyncio.wait_for does not preempt it —
  the event loop stays blocked regardless of the timeout you set.

  ⚠️ CORRECTNESS-CRITICAL (v2): expose availability via a FUNCTION, never a raw module-level
  bool that other modules import by value. `from src.search.client import search_available`
  captures the value at import time and never sees later changes.

  import asyncio
  import structlog
  from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
  from qdrant_client import AsyncQdrantClient, models as qmodels
  from src.config import get_settings

  log = structlog.get_logger()

  _client: AsyncQdrantClient | None = None
  _qdrant_available: bool = False  # pessimistic until ensure_places_collection() succeeds

  def get_qdrant_client() -> AsyncQdrantClient:
      """Lazy singleton, same pattern as core/database/session.py's get_engine()."""
      global _client
      if _client is None:
          settings = get_settings()
          _client = AsyncQdrantClient(
              url=settings.QDRANT_URL,
              api_key=settings.QDRANT_API_KEY or None,
          )
      return _client

  def is_qdrant_available() -> bool:
      """The ONLY sanctioned way for other modules to check Qdrant availability."""
      return _qdrant_available

  def _set_qdrant_available(value: bool) -> None:
      global _qdrant_available
      _qdrant_available = value

  @retry(
      stop=stop_after_attempt(2),   # literal matches QDRANT_OPERATION_MAX_RETRIES default —
      wait=wait_fixed(1),           # keep both in sync if either changes, same convention as
      retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),  # LLM_MAX_RETRIES
  )
  async def _ensure_collection_impl() -> None:
      settings = get_settings()
      client = get_qdrant_client()
      exists = await asyncio.wait_for(
          client.collection_exists(settings.QDRANT_PLACES_COLLECTION),
          timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
      )
      if not exists:
          await asyncio.wait_for(
              client.create_collection(
                  collection_name=settings.QDRANT_PLACES_COLLECTION,
                  vectors_config=qmodels.VectorParams(
                      size=settings.PLACES_EMBEDDING_DIM,
                      distance=qmodels.Distance.COSINE,
                  ),
              ),
              timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
          )

  async def ensure_places_collection() -> None:
      """
      MUST be safe to call during FastAPI lifespan startup — never raises.
      On any connectivity/auth/misconfig error after retries: log warning,
      set is_qdrant_available() to False, do NOT raise.
      """
      try:
          await _ensure_collection_impl()
          _set_qdrant_available(True)
      except Exception as exc:
          log.warning("qdrant.ensure_collection_failed", error=str(exc))
          _set_qdrant_available(False)

  async def close_qdrant_client() -> None:
      """Call from lifespan shutdown — mirrors dispose_engine()."""
      global _client
      if _client is not None:
          await _client.close()
          _client = None

─── UPDATE src/config.py + .env.example ───
Add all Config additions listed in the P3 design decisions section above (QDRANT_URL,
QDRANT_API_KEY, QDRANT_PLACES_COLLECTION, PLACES_EMBEDDING_DIM,
QDRANT_OPERATION_TIMEOUT_SECONDS, QDRANT_OPERATION_MAX_RETRIES).

IMPORTANT: `QDRANT_URL` / `QDRANT_API_KEY` already exist in `src/config.py` with a wrong
host default (`http://localhost:6333`). Change the default to `http://localhost:6335`
(compose host mapping). Keep a single `QDRANT_URL` setting — do not add a duplicate key.
`.env.example` already uses `6335`; keep it aligned when adding the new keys.

─── UPDATE src/main.py lifespan ───
  from src.search.client import ensure_places_collection, close_qdrant_client
  # in startup:
  await ensure_places_collection()
  # in shutdown:
  await close_qdrant_client()

─── RULES ───
- Never raise from `ensure_places_collection()` (fail-soft).
- Never hardcode Qdrant collection name or vector size in code (use config).
- Nothing outside this file imports `_qdrant_available` directly — only `is_qdrant_available()`.

─── FAILURE BOUNDARY ───
Qdrant unreachable → app continues, semantic search degrades:
✅ Failure path: mock the qdrant client call to raise a connection error during ensure.
Ensure: server starts; `is_qdrant_available()` returns False; `search_places(...)` (step 3.4)
returns `[]` later.

─── VALIDATION ───
Run (with docker compose Qdrant running):
  python -c "
import asyncio
from src.search.client import ensure_places_collection, get_qdrant_client, is_qdrant_available
async def main():
    await ensure_places_collection()
    assert is_qdrant_available() is True
    client = get_qdrant_client()
    cols = await client.get_collections()
    names = [c.name for c in cols.collections]
    assert 'places' in names
    print('PASS — Qdrant collection ensured, availability flag correct')
asyncio.run(main())
"

✅ Failure path — connectivity failure sets the flag correctly, live (not a stale copy):
  python -c "
import asyncio
from unittest.mock import AsyncMock, patch
from src.search.client import ensure_places_collection, is_qdrant_available, _set_qdrant_available

async def main():
    _set_qdrant_available(True)  # reset
    with patch('src.search.client._ensure_collection_impl', new_callable=AsyncMock, side_effect=ConnectionError('down')):
        await ensure_places_collection()
        assert is_qdrant_available() is False
    print('PASS — failure correctly flips is_qdrant_available() to False')

asyncio.run(main())
"
```

---

## Step 3.2 — search/embeddings.py — embed_text/embed_batch, thread-offloaded

```
Read AGENT.md before proceeding.

TASK: Implement embedding abstraction using sentence-transformers with fail-soft behavior,
CPU-bound calls offloaded to a thread, and explicit bounded model loading from lifespan
(not implicit at import time).
This is step 3.2.

─── INSTALL ───
Append to requirements.txt:
  sentence-transformers==5.1.2   # embeddings for place knowledge layer

Install:
  pip install sentence-transformers==5.1.2

─── UPDATE src/config.py + .env.example ───
Add `PLACES_EMBEDDING_MODEL` and `PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS` (see design
decisions section above).

─── IMPLEMENT src/search/embeddings.py ───

  ⚠️ CORRECTNESS-CRITICAL (v2): SentenceTransformer.encode() is synchronous and CPU-bound.
  Calling it directly inside an `async def` blocks the entire event loop — including every
  other concurrent request — for the full duration of inference. Always offload via
  asyncio.to_thread.

  ⚠️ CORRECTNESS-CRITICAL (v2): model loading is NOT automatic at import time. It is an
  explicit async function called once from lifespan, bounded by a timeout, fail-soft.

  import asyncio
  import structlog
  from sentence_transformers import SentenceTransformer
  from src.config import get_settings

  log = structlog.get_logger()

  _model: SentenceTransformer | None = None
  _embeddings_available: bool = False

  def is_embeddings_available() -> bool:
      """The ONLY sanctioned way for other modules to check embedding availability."""
      return _embeddings_available

  async def ensure_embedding_model_loaded() -> None:
      """
      Call once from lifespan startup, alongside ensure_places_collection().
      Never raises. Do NOT retry inside this function (a failed load is a permanent-until-
      restart condition — env/network/disk issue, not transient).
      """
      global _model, _embeddings_available
      settings = get_settings()
      try:
          _model = await asyncio.wait_for(
              asyncio.to_thread(SentenceTransformer, settings.PLACES_EMBEDDING_MODEL),
              timeout=settings.PLACES_EMBEDDING_MODEL_LOAD_TIMEOUT_SECONDS,
          )
          _embeddings_available = True
      except Exception as exc:
          log.warning("embeddings.model_load_failed", error=str(exc))
          _model = None
          _embeddings_available = False

  async def embed_text(text: str) -> list[float]:
      """Returns [] if embeddings unavailable or text is blank. Never raises."""
      if not _embeddings_available or not text.strip():
          return []
      vector = await asyncio.to_thread(_model.encode, text)
      return vector.tolist()

  async def embed_batch(texts: list[str]) -> list[list[float]]:
      """
      LOCKED (v2): parallel-array contract — one output per input, in order.
      Unavailable -> [[] for _ in texts], never a bare [].
      """
      if not _embeddings_available:
          return [[] for _ in texts]
      vectors = await asyncio.to_thread(_model.encode, texts)
      return [v.tolist() for v in vectors]

─── UPDATE src/main.py lifespan ───
  from src.search.embeddings import ensure_embedding_model_loaded
  # in startup, alongside ensure_places_collection():
  await ensure_embedding_model_loaded()

─── RULES ───
- Never raise from `embed_text`/`embed_batch`/`ensure_embedding_model_loaded`.
- Output vector length must match `PLACES_EMBEDDING_DIM` (384) when available.
- No code outside this file imports `_model` or `_embeddings_available` directly.
- Production runbook note: pre-bake the model into the Docker image build to avoid a runtime
  download on a resource-constrained host — document this in docs/context.md.

─── FAILURE BOUNDARY ───
Embedding model load failure:
✅ Failure path: force a load failure, assert `embed_text(...) == []` and
`embed_batch([...]) == [[] , []]` (parallel-array shape preserved even when empty).

─── VALIDATION ───
Run:
  python -c "
import asyncio
from src.search.embeddings import ensure_embedding_model_loaded, embed_text, embed_batch, is_embeddings_available

async def main():
    await ensure_embedding_model_loaded()
    assert is_embeddings_available() is True
    v = await embed_text('sunrise photography')
    assert isinstance(v, list) and len(v) == 384
    batch = await embed_batch(['a', 'b', 'c'])
    assert len(batch) == 3 and all(len(x) == 384 for x in batch)
    print('PASS — embeddings vector length', len(v), 'batch shape', [len(x) for x in batch])

asyncio.run(main())
"

✅ Failure path — degraded mode preserves the parallel-array contract:
  python -c "
import asyncio
from src.search import embeddings

async def main():
    embeddings._model = None
    embeddings._embeddings_available = False
    assert await embeddings.embed_text('x') == []
    batch = await embeddings.embed_batch(['a', 'b'])
    assert batch == [[], []], f'expected parallel empty arrays, got {batch}'
    print('PASS — degraded mode returns [] / [[],[]], never a bare [] for batch')

asyncio.run(main())
"
```

---

## Step 3.3 — places/service.py — enrich_place() (LLM+parse split, malformed-JSON handling)

```
Read AGENT.md before proceeding.

TASK: Extend PlaceService with enrich_place(), split into an LLM-call-and-parse-only method
(so the batch script in 3.5 can run it concurrently) and a persistence wrapper. Handles both
LLM-call failure and malformed-output failure as distinct, logged failure modes.
This is step 3.3.

─── CREATE src/places/constants.py ───

  """
  Domain constants — mirrors travel_engine/travel_rules.py's precedent: fixed business rules
  live here, not in Settings/.env (see locked P3 design decision).
  """
  PLACE_TAG_VOCAB: list[str] = [
      "offbeat", "photography", "viewpoint", "trek", "monastery",
      "cultural", "family", "nature", "adventure",
  ]

─── IMPLEMENT src/places/service.py additions ───

  import json
  from dataclasses import dataclass
  import structlog
  from src.core.llm.client import chat_completion   # module-scope import — patchable in tests
  from src.core.exceptions import WandrLLMError
  from src.places.constants import PLACE_TAG_VOCAB
  from src.places.models import Place

  log = structlog.get_logger()

  @dataclass(frozen=True)
  class ParsedEnrichment:
      summary: str
      tags: list[str]

  class PlaceService:
      # ... existing __init__ already sets self.repo = PlaceRepository(session) ...

      async def _call_llm_and_parse(self, place: Place) -> ParsedEnrichment | None:
          """
          LLM call + JSON parse + vocab filtering ONLY. No DB read/write. This split exists
          so the batch script (3.5) can run this concurrently across many places while
          keeping the actual DB write serialized on one session.
          """
          prompt = [
              {"role": "user", "content": (
                  f"Place name: {place.name}\nCategory: {place.category}\n"
                  f"Raw tags: {place.tags}\n\n"
                  "Return a JSON object with exactly two keys: "
                  '"summary" (1-3 sentence description) and '
                  f'"tags" (a list of zero or more values from this exact vocabulary: {PLACE_TAG_VOCAB}).'
              )}
          ]
          try:
              raw = await chat_completion(messages=prompt, response_format={"type": "json_object"})
          except WandrLLMError as e:
              log.warning("enrichment.llm_failed", place_id=str(place.id), error=str(e))
              return None

          try:
              data = json.loads(raw)
              summary = str(data["summary"]).strip()
              if not summary:
                  raise ValueError("empty summary")
              raw_tags = data.get("tags", [])
              if not isinstance(raw_tags, list):
                  raise TypeError("tags must be a list")
          except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
              # DISTINCT failure mode from WandrLLMError — the LLM responded, but the
              # response is unusable. Logged separately so the two causes aren't conflated.
              log.warning("enrichment.malformed_response", place_id=str(place.id), error=str(e))
              return None

          filtered_tags = [t for t in raw_tags if t in PLACE_TAG_VOCAB]
          # An empty filtered_tags list is a VALID outcome (no vocab match) — not a failure.
          return ParsedEnrichment(summary=summary, tags=filtered_tags)

      async def enrich_place(self, place: Place) -> tuple[str, list[str]] | None:
          """
          Re-runnable: places with summary already set are skipped (LLM not called).
          Persists to place.summary and place.enriched_tags ONLY — place.tags (raw OSM
          dict) is never touched. Flush-only; caller commits.
          """
          if place.summary is not None:
              return None
          parsed = await self._call_llm_and_parse(place)
          if parsed is None:
              return None
          await self.repo.update(place.id, {
              "summary": parsed.summary,
              "enriched_tags": parsed.tags,
          })
          return parsed.summary, parsed.tags

─── RULES ───
- LLM only through `src/core/llm/client.py`; imported at module scope in this file so tests
  can patch `src.places.service.chat_completion`.
- `enrich_place` NEVER assigns to `place.tags` — only `place.summary` and `place.enriched_tags`.
- Empty `enriched_tags` after vocab filtering is persisted as a success, not skipped.
- Malformed LLM output and `WandrLLMError` are handled and logged as DISTINCT failure modes.

─── FAILURE BOUNDARY ───
Per-place enrichment failure is contained, for BOTH failure modes:
✅ Failure path 1: mock chat_completion to raise WandrLLMError — enrich_place returns None,
   no DB write attempted.
✅ Failure path 2: mock chat_completion to return non-JSON text (or JSON missing "summary")
   — enrich_place returns None, no DB write attempted, logged under "enrichment.malformed_response".

─── VALIDATION ───

Zero-happy-path validation (fully mocked; no DB + no real LLM):

  python -c "
import asyncio, uuid, json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from src.places.service import PlaceService
from src.core.exceptions import WandrLLMError

async def main():
    session = AsyncMock()
    svc = PlaceService(session)
    svc.repo.update = AsyncMock()

    # 1) Re-runnable skip: summary already set -> LLM not called
    place_skip = SimpleNamespace(id=uuid.uuid4(), name='X', category='viewpoint',
        tags={'tourism':'viewpoint'}, summary='already-enriched', destination_id=uuid.uuid4())
    with patch('src.places.service.chat_completion', new=AsyncMock()) as mock_llm:
        r1 = await svc.enrich_place(place_skip)
        assert r1 is None and mock_llm.await_count == 0

    # 2) LLM call failure -> None, no DB write (distinct failure mode #1)
    place_fail = SimpleNamespace(id=uuid.uuid4(), name='Y', category='viewpoint',
        tags={'tourism':'viewpoint'}, summary=None, destination_id=uuid.uuid4())
    with patch('src.places.service.chat_completion',
               new=AsyncMock(side_effect=WandrLLMError(code='llm_unavailable', message='boom'))):
        r2 = await svc.enrich_place(place_fail)
        assert r2 is None and svc.repo.update.await_count == 0

    # 3) Malformed JSON output -> None, no DB write (distinct failure mode #2 — v2 addition)
    place_malformed = SimpleNamespace(id=uuid.uuid4(), name='M', category='viewpoint',
        tags={}, summary=None, destination_id=uuid.uuid4())
    with patch('src.places.service.chat_completion', new=AsyncMock(return_value='not even json')):
        r3 = await svc.enrich_place(place_malformed)
        assert r3 is None and svc.repo.update.await_count == 0

    # 4) Happy parsing with unknown tag filtered out, known tag kept
    place_ok = SimpleNamespace(id=uuid.uuid4(), name='Z', category='viewpoint',
        tags={'tourism':'viewpoint'}, summary=None, destination_id=uuid.uuid4())
    with patch('src.places.service.chat_completion',
               new=AsyncMock(return_value=json.dumps({'summary':'S','tags':['photography','not-in-vocab']}))):
        r4 = await svc.enrich_place(place_ok)
        assert r4 == ('S', ['photography'])
        assert svc.repo.update.await_count == 1
        call_kwargs = svc.repo.update.await_args.args[1]
        assert call_kwargs == {'summary': 'S', 'enriched_tags': ['photography']}
        assert 'tags' not in call_kwargs, 'enrich_place must never write to place.tags'

    # 5) Empty tags after filtering is a SUCCESS, not a skip (v2 locked rule)
    place_no_match = SimpleNamespace(id=uuid.uuid4(), name='N', category='attraction',
        tags={}, summary=None, destination_id=uuid.uuid4())
    with patch('src.places.service.chat_completion',
               new=AsyncMock(return_value=json.dumps({'summary':'Generic place.','tags':['not-in-vocab']}))):
        r5 = await svc.enrich_place(place_no_match)
        assert r5 == ('Generic place.', [])
        print('PASS — empty-tags-after-filter is persisted as success, not skipped')

    print('PASS — skip / LLM-failure / malformed-output / happy-path / empty-tags all correct')

asyncio.run(main())
"
```

---

## Step 3.4 — search/places_index.py — single + batch upsert, semantic search, ground-truth count

```
Read AGENT.md before proceeding.

TASK: Implement Qdrant upsert (single AND batch), destination-scoped semantic search, and a
ground-truth indexed-count query — all using the function-based availability checks from
3.1/3.2, never a raw imported boolean.
This is step 3.4.

─── IMPLEMENT src/search/places_index.py ───

  import asyncio, uuid
  from dataclasses import dataclass
  import structlog
  from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
  from qdrant_client import models as qmodels

  from src.config import get_settings
  from src.search.client import get_qdrant_client, is_qdrant_available
  from src.search.embeddings import embed_text, embed_batch
  from src.places.models import Place

  log = structlog.get_logger()

  @dataclass
  class PlaceSearchResult:
      place_id: str
      score: float
      name: str | None = None
      destination_id: str | None = None

  def _canonical_text(place: Place) -> str:
      """Embed text is derived from ENRICHED output only — enriched_tags, never raw tags."""
      tags_csv = ", ".join(place.enriched_tags or [])
      return f"{place.summary}\n{tags_csv}"

  def _payload_for(place: Place, destination_id: uuid.UUID) -> dict:
      return {
          "destination_id": str(destination_id),
          "place_id": str(place.id),
          "name": place.name,
          "osm_id": place.osm_id,
          "category": place.category,
      }

  @retry(stop=stop_after_attempt(2), wait=wait_fixed(1),
         retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)))
  async def _upsert_points_impl(points: list) -> None:
      settings = get_settings()
      client = get_qdrant_client()
      await asyncio.wait_for(
          client.upsert(collection_name=settings.QDRANT_PLACES_COLLECTION, points=points),
          timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
      )

  async def _upsert_points(points: list) -> bool:
      if not points:
          return False
      try:
          await _upsert_points_impl(points)
          return True
      except Exception as e:
          log.warning("qdrant.upsert_failed", error=str(e), count=len(points))
          return False

  async def upsert_place(place: Place, destination_id: uuid.UUID) -> bool:
      """
      Single-place upsert — kept for callers needing to re-index one place (e.g. a future
      P7 edit-triggered re-index). Deterministic point_id = str(place.id).
      """
      if not place.summary:
          return False
      vector = await embed_text(_canonical_text(place))
      if not vector:
          return False
      point = qmodels.PointStruct(id=str(place.id), vector=vector, payload=_payload_for(place, destination_id))
      return await _upsert_points([point])

  async def upsert_places_batch(places: list[Place], destination_id: uuid.UUID) -> int:
      """
      NEW (v2): batches embedding (embed_batch, previously-unused) AND the Qdrant write
      (one upsert call for the whole chunk instead of N single-item calls). Real throughput
      win on CPU-only hosts — sentence-transformers batches efficiently; Qdrant supports
      batch upsert natively. Returns count of points actually written.
      """
      eligible = [p for p in places if p.summary]
      if not eligible:
          return 0
      texts = [_canonical_text(p) for p in eligible]
      vectors = await embed_batch(texts)   # parallel array — see locked contract
      points = [
          qmodels.PointStruct(id=str(place.id), vector=vector, payload=_payload_for(place, destination_id))
          for place, vector in zip(eligible, vectors)
          if vector   # skip any place whose embedding came back empty (degraded mode)
      ]
      if not points:
          return 0
      ok = await _upsert_points(points)
      return len(points) if ok else 0

  async def search_places(query: str, destination_id: uuid.UUID, top_k: int = 10) -> list[PlaceSearchResult]:
      if not is_qdrant_available():
          return []
      vector = await embed_text(query)
      if not vector:
          return []
      try:
          settings = get_settings()
          client = get_qdrant_client()
          results = await asyncio.wait_for(
              client.search(
                  collection_name=settings.QDRANT_PLACES_COLLECTION,
                  query_vector=vector,
                  query_filter=qmodels.Filter(must=[
                      qmodels.FieldCondition(key="destination_id", match=qmodels.MatchValue(value=str(destination_id))),
                  ]),
                  limit=top_k,
              ),
              timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
          )
      except Exception as e:
          log.warning("qdrant.search_failed", error=str(e))
          return []
      return [
          PlaceSearchResult(place_id=r.payload["place_id"], score=r.score,
                            name=r.payload.get("name"), destination_id=r.payload.get("destination_id"))
          for r in results
      ]

  async def count_indexed(destination_id: uuid.UUID) -> int:
      """
      NEW (v2): ground truth for Destination.indexed_count, mirroring how enriched_count is
      already recomputed from DB truth rather than a per-run tally. Prevents indexed_count
      from understating the true state after a --limit-bounded or partial run.
      """
      if not is_qdrant_available():
          return 0
      try:
          settings = get_settings()
          client = get_qdrant_client()
          result = await asyncio.wait_for(
              client.count(
                  collection_name=settings.QDRANT_PLACES_COLLECTION,
                  count_filter=qmodels.Filter(must=[
                      qmodels.FieldCondition(key="destination_id", match=qmodels.MatchValue(value=str(destination_id))),
                  ]),
              ),
              timeout=settings.QDRANT_OPERATION_TIMEOUT_SECONDS,
          )
          return result.count
      except Exception as e:
          log.warning("qdrant.count_failed", error=str(e))
          return 0

─── RULES ───
- Deterministic idempotency: same place always maps to the same point_id.
- Destination-scoped search filter is mandatory, not optional.
- Availability checked via `is_qdrant_available()` — never a raw imported boolean.
- Embed text is derived from `enriched_tags`, never the raw `tags` dict.
- Module scope imports (`get_qdrant_client`, `embed_text`, `embed_batch`, `is_qdrant_available`)
  so tests can patch `src.search.places_index.<name>`.

─── FAILURE BOUNDARY ───
✅ Failure path 1: mock qdrant client search to raise — search_places returns [] without raising.
✅ Failure path 2: mock embedding to return [] — search_places returns [] and does not call
   qdrant search at all (short-circuits before the network call).
✅ Failure path 3: mock is_qdrant_available() to return False — search_places returns []
   without even attempting to embed the query (cheapest possible short-circuit).

─── VALIDATION ───

Zero-happy-path validation (mocked; no live Qdrant needed):

  python -c "
import asyncio, uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from src.search.places_index import upsert_place, upsert_places_batch, search_places, count_indexed

async def main():
    dest_id = uuid.uuid4()
    place = SimpleNamespace(id=uuid.uuid4(), summary='S', enriched_tags=['photography'],
        name='N', osm_id='node/1', category='viewpoint')
    place2 = SimpleNamespace(id=uuid.uuid4(), summary='S2', enriched_tags=[],
        name='N2', osm_id='node/2', category='museum')

    mock_client = AsyncMock()
    mock_client.upsert = AsyncMock()
    mock_client.search = AsyncMock(side_effect=RuntimeError('qdrant down'))
    mock_client.count = AsyncMock(return_value=SimpleNamespace(count=2))

    with patch('src.search.places_index.get_qdrant_client', return_value=mock_client), \\
         patch('src.search.places_index.embed_text', new=AsyncMock(return_value=[0.0]*384)), \\
         patch('src.search.places_index.embed_batch', new=AsyncMock(return_value=[[0.0]*384, [0.0]*384])), \\
         patch('src.search.places_index.is_qdrant_available', return_value=True):

        # Idempotent single upsert
        ok1 = await upsert_place(place, dest_id)
        ok2 = await upsert_place(place, dest_id)
        assert ok1 is True and ok2 is True

        # NEW: batch upsert does ONE qdrant call for the whole chunk, uses embed_batch
        mock_client.upsert.reset_mock()
        count = await upsert_places_batch([place, place2], dest_id)
        assert count == 2
        assert mock_client.upsert.await_count == 1, 'batch must be a single upsert call, not N'

        # Qdrant search failure degrades to []
        res = await search_places('photography', dest_id, top_k=3)
        assert res == []

        # Ground-truth count via Qdrant, not a run tally
        idx_count = await count_indexed(dest_id)
        assert idx_count == 2

    # Embedding failure degrades to [] and never reaches qdrant.search
    mock_client.search.reset_mock()
    with patch('src.search.places_index.get_qdrant_client', return_value=mock_client), \\
         patch('src.search.places_index.embed_text', new=AsyncMock(return_value=[])), \\
         patch('src.search.places_index.is_qdrant_available', return_value=True):
        res2 = await search_places('photography', dest_id, top_k=3)
        assert res2 == [] and mock_client.search.await_count == 0

    # is_qdrant_available()=False short-circuits before even embedding
    with patch('src.search.places_index.is_qdrant_available', return_value=False), \\
         patch('src.search.places_index.embed_text', new=AsyncMock()) as mock_embed:
        res3 = await search_places('photography', dest_id, top_k=3)
        assert res3 == [] and mock_embed.await_count == 0

    print('PASS — single/batch upsert idempotency, [] degradation at every layer, ground-truth count')

asyncio.run(main())
"
```

---

## Step 3.5 — scripts/enrich_places.py + scripts/index_places.py

```
Read AGENT.md before proceeding.

TASK: Implement re-runnable batch scripts. Enrichment runs LLM calls concurrently (bounded)
while keeping DB writes serialized with per-item savepoints; indexing uses the new batch
upsert path and ground-truth Qdrant counting. Both scripts correctly treat limit=0 as
"unlimited," never as ".limit(0)".
This is step 3.5.

─── IMPLEMENT scripts/enrich_places.py ───

CLI:
  python scripts/enrich_places.py --destination "Darjeeling" --batch-size 10 --limit 0

Exposed, session-injected, testable helper:

  async def enrich_places(session: AsyncSession, destination_id: uuid.UUID,
                           batch_size: int, limit: int) -> int:
      """Does NOT open session and does NOT commit — caller (CLI wrapper) owns commit."""
      settings = get_settings()
      stmt = select(Place).where(Place.destination_id == destination_id, Place.summary.is_(None))
      if limit and limit > 0:          # LOCKED (v2): NEVER call .limit(0) — see design decisions
          stmt = stmt.limit(limit)
      places = list((await session.execute(stmt)).scalars().all())

      service = PlaceService(session)
      semaphore = asyncio.Semaphore(settings.ENRICH_BATCH_LLM_CONCURRENCY)
      success = 0

      for i in range(0, len(places), batch_size):
          chunk = places[i:i + batch_size]

          async def _parse_one(place):
              async with semaphore:
                  return place, await service._call_llm_and_parse(place)

          # Network-bound step (slow, IO-bound) runs concurrently, bounded.
          results = await asyncio.gather(*[_parse_one(p) for p in chunk])

          # DB-write step stays sequential on the ONE shared session, each item isolated
          # by a SAVEPOINT (v2 locked rule) so one bad write can't poison the whole batch.
          for place, parsed in results:
              if parsed is None:
                  continue
              try:
                  async with session.begin_nested():
                      await service.repo.update(place.id, {
                          "summary": parsed.summary,
                          "enriched_tags": parsed.tags,
                      })
                  success += 1
              except Exception as e:
                  log.warning("enrich.persist_failed", place_id=str(place.id), error=str(e))
                  continue

          if (i + batch_size) % 50 == 0 or (i + batch_size) >= len(places):
              print(f"  ... {min(i + batch_size, len(places))}/{len(places)} processed")

      # Recompute enriched_count from DB truth (unchanged from v1 — this part was correct).
      enriched_total = await session.scalar(
          select(func.count()).select_from(Place).where(
              Place.destination_id == destination_id, Place.summary.is_not(None),
          )
      )
      await DestinationRepository(session).update(destination_id, {"enriched_count": enriched_total})
      return success

CLI wrapper: opens AsyncSessionLocal(), calls enrich_places(), commits, prints
  "Enriched {success}/{total} places for {destination_name}".

─── IMPLEMENT scripts/index_places.py ───

CLI:
  python scripts/index_places.py --destination "Darjeeling" --batch-size 10 --limit 0

Exposed, session-injected, testable helper:

  async def index_places(session: AsyncSession, destination_id: uuid.UUID,
                          batch_size: int, limit: int) -> int:
      """Does NOT open session and does NOT commit."""
      stmt = select(Place).where(Place.destination_id == destination_id, Place.summary.is_not(None))
      if limit and limit > 0:          # LOCKED (v2): same guard as enrich_places
          stmt = stmt.limit(limit)
      places = list((await session.execute(stmt)).scalars().all())

      total_success = 0
      for i in range(0, len(places), batch_size):
          chunk = places[i:i + batch_size]
          # NEW (v2): one batched embed + one batched qdrant upsert per chunk, not N singles.
          total_success += await upsert_places_batch(chunk, destination_id)

      # Ground truth from Qdrant itself (v2 fix) — not "this run's success tally", which
      # would understate the true state after any --limit-bounded or partial run.
      indexed_total = await count_indexed(destination_id)
      await DestinationRepository(session).update(destination_id, {"indexed_count": indexed_total})
      return total_success

CLI wrapper prints "Indexed {success}/{total} places for {destination_name}
  (Qdrant ground truth: {indexed_total})".

LOCKED (v2): if Qdrant/embeddings are unavailable, indexed_total ends up 0 — this is a
DEGRADED MODE, not a hard failure. Print a clear warning line but exit 0, consistent with
every other "Qdrant unavailable" resilience contract in this codebase (a hard non-zero exit
here would be the only inconsistent case in the whole system).

─── RULES ───
- Scripts commit only in the CLI wrapper (unchanged convention from scripts/seed_destination.py).
- Re-runnable: enrichment never overwrites an existing summary; indexing's deterministic
  point_id makes re-runs idempotent.
- `.limit(0)` is never called anywhere in either script.
- Per-item DB writes in `enrich_places` are wrapped in `session.begin_nested()`.

─── FAILURE BOUNDARY ───
✅ Failure path 1 (the missing v1 test): a single place's DB write raising mid-batch must not
   abort the rest of the batch, AND must not poison the shared transaction for subsequent
   places (this is the specific SAVEPOINT regression test — see Step "P3 Testing Plan" below
   for the pytest version; the smoke check here uses a direct call).
✅ Failure path 2: `--limit 0` must process ALL eligible places, not zero.

─── VALIDATION ───

✅ v2 regression test — limit=0 means unlimited, never zero rows:
  python -c "
import asyncio
from sqlalchemy import select
from src.places.models import Place

def build_stmt(limit):
    stmt = select(Place)
    if limit and limit > 0:
        stmt = stmt.limit(limit)
    return stmt

stmt_zero = build_stmt(0)
stmt_none = build_stmt(None)
stmt_five = build_stmt(5)

assert stmt_zero._limit_clause is None, 'limit=0 must NOT apply .limit(0) to the query'
assert stmt_none._limit_clause is None
assert stmt_five._limit_clause is not None
print('PASS — limit=0/None means unlimited, only a positive limit applies .limit()')
"

Manual smoke flow (network + LLM required):
1) Seed destination places (P2):
   python scripts/seed_destination.py --destination "Darjeeling" --radius 30
2) Enrich (LLM required):
   python scripts/enrich_places.py --destination "Darjeeling" --limit 5
3) Index (Qdrant required):
   python scripts/index_places.py --destination "Darjeeling" --limit 20
4) Semantic search check (manual, in a REPL):
   from src.search.places_index import search_places
   # results = await search_places("photography sunrise", destination_id, top_k=5)
   # assert results and all(r.destination_id == str(destination_id) for r in results)
```

---

## Step 3.6 — Wire readiness endpoint to real search availability ★ NEW (v2, closes the P2→P3 gap)

```
Read AGENT.md before proceeding.

TASK: P2's readiness.py explicitly documented that tier=ready requires P3 enrichment and
indexing — but no P3 step ever updates DestinationService.get_readiness(), which still
hardcodes search_available=False forever. This step closes that loop. Without it, the
readiness endpoint would never report anything but tier=limited even after full P3 work —
a real feature-completeness gap, not just a code-quality nitpick.
This is step 3.6. No package installs.

─── UPDATE src/destinations/service.py ───

  from src.search.client import is_qdrant_available   # one-way dependency: destinations may
                                                        # read search's status; search must
                                                        # NEVER import from destinations.

  async def get_readiness(self, destination_id: uuid.UUID) -> DestinationReadinessOut:
      dest = await self.repo.get_by_id_or_raise(destination_id)
      search_available = is_qdrant_available()   # WAS hardcoded False in P2 — now real (v2 fix)
      result = compute_readiness(
          dest.place_count, dest.enriched_count, dest.indexed_count, search_available,
      )
      return DestinationReadinessOut(
          destination_id=dest.id,
          score=result.score,
          tier=result.tier,
          place_count=result.place_count,
          enriched_pct=result.enriched_pct,
          indexed_pct=result.indexed_pct,
          message=result.message,
      )

─── RULES ───
- This is a status READ only — destinations/service.py does not call any Qdrant write
  operations and does not import anything else from search/ beyond is_qdrant_available().
- src/search/ must never import from src/destinations/ — keep the dependency graph acyclic.
- No change to `readiness.py` itself (the pure `compute_readiness` function is unchanged) —
  only the value fed into it changes.

─── FAILURE BOUNDARY ───
Qdrant down at the moment of the readiness check → search_available=False → indexed_pct
component drops out of the score, tier degrades gracefully to whatever place/enriched
components alone justify. Endpoint still returns 200 — this was already true in P2 and
remains true here; nothing about this step should make readiness fail loudly.
Must NOT: raise if Qdrant is down; must NOT call any Qdrant write path from this method.

─── VALIDATION ───
This closes the exact scenario P2's own documentation promised. After running Step 3.5's
full enrich + index flow for Darjeeling:

  curl -s "http://localhost:8000/api/v1/destinations/{DESTINATION_ID}/readiness" | python -m json.tool

Expected (this is the key end-to-end proof for all of P3): with `enriched_count` and
`indexed_count` both reasonably close to `place_count` (e.g. run enrich_places/index_places
without --limit, or with a --limit high enough to cover most seeded places), and Qdrant
reachable:

  tier should now be able to reach "ready" (score >= 0.7) — where in P2 it was
  PERMANENTLY CAPPED at "limited" regardless of enrichment/indexing work done.

Unit-level proof (no live Qdrant needed).

  NOTE on readiness math (locked P2 formula): score = 0.4*place + 0.35*enriched + 0.25*indexed.
  place+enriched alone can already reach score ≥ 0.7 (tier=ready) without the indexed term.
  Qdrant-down therefore MUST assert `indexed_pct == 0.0` (indexed DB counter does not contribute).
  Do NOT assert tier ∈ {limited, sparse} on a high place+enriched fixture — that assertion is false
  under the locked formula. Use a separate fixture where place+enriched alone stay below 0.7 if
  you also want to prove a non-ready tier when search is unavailable.

  python -c "
import asyncio, uuid
from unittest.mock import AsyncMock, patch
from src.destinations.service import DestinationService
from types import SimpleNamespace

async def main():
    session = AsyncMock()
    svc = DestinationService(session)

    # Fixture A: high place+enriched+indexed → ready when Qdrant is up
    ready_dest = SimpleNamespace(id=uuid.uuid4(), place_count=144, enriched_count=140, indexed_count=140)
    svc.repo.get_by_id_or_raise = AsyncMock(return_value=ready_dest)

    with patch('src.destinations.service.is_qdrant_available', return_value=True):
        out = await svc.get_readiness(ready_dest.id)
        assert out.tier == 'ready', f'expected ready, got {out.tier} (score={out.score})'

    # Same high counts, Qdrant down → indexed term drops out; tier may still be ready
    # because place+enriched alone can score ≥ 0.7 under the locked formula.
    with patch('src.destinations.service.is_qdrant_available', return_value=False):
        out2 = await svc.get_readiness(ready_dest.id)
        assert out2.indexed_pct == 0.0
        assert out2.score < out.score, 'dropping indexed component must lower the score'

    # Fixture B: place+enriched alone stay under 0.7; with search up + high indexed → ready;
    # with search down → limited/sparse (proves the live flag gates the indexed term).
    gated_dest = SimpleNamespace(id=uuid.uuid4(), place_count=80, enriched_count=40, indexed_count=80)
    svc.repo.get_by_id_or_raise = AsyncMock(return_value=gated_dest)

    with patch('src.destinations.service.is_qdrant_available', return_value=True):
        out3 = await svc.get_readiness(gated_dest.id)
        assert out3.tier == 'ready', f'expected ready with indexed term, got {out3.tier} (score={out3.score})'

    with patch('src.destinations.service.is_qdrant_available', return_value=False):
        out4 = await svc.get_readiness(gated_dest.id)
        assert out4.indexed_pct == 0.0
        assert out4.tier in ('limited', 'sparse'), f'expected non-ready without indexed term, got {out4.tier}'

    print('PASS — readiness reaches ready; Qdrant-down zeros indexed_pct; gated fixture proves tier drop')

asyncio.run(main())
"
```

---

## P3 Testing Plan (pytest, mocked external dependencies, expanded in v2)

Implement pytest coverage that is deterministic and does NOT depend on live Qdrant, a
downloaded sentence-transformers model, or a real LLM provider.

- `tests/places/test_places_model.py` ★ NEW
  - `test_tags_and_enriched_tags_are_distinct_columns` — asserts both columns exist and are
    independently settable (regression test for the v1 schema-mismatch bug).

- `tests/search/test_client.py` ★ NEW
  - `test_is_qdrant_available_reflects_live_state_across_modules` — flips availability via
    `client.py`'s setter, asserts a *second module* that calls `is_qdrant_available()`
    (not one that imported a raw boolean) observes the change immediately. This is the
    direct regression test for the v1 stale-import bug.

- `tests/search/test_embeddings.py`
  - `embed_text` returns `[]` when the model is unavailable.
  - `embed_text` returns a 384-length vector when the model is mocked.
  - `embed_batch` returns a parallel array of empty lists (not a bare `[]`) when unavailable.
  - ★ NEW `test_embed_text_does_not_block_event_loop` — patch `_model.encode` with a mock
    that sleeps briefly via a threading.Event, run `embed_text` concurrently with another
    coroutine, assert the other coroutine's progress isn't stalled (proves `to_thread` is
    actually being used, not just present in the source).

- `tests/search/test_places_index.py`
  - `upsert_place` returns `False` when embedding returns `[]`.
  - `upsert_place` uses deterministic `point_id = str(place.id)`.
  - ★ NEW `upsert_places_batch` issues exactly ONE `client.upsert` call for a chunk of N
    places (not N calls) — regression test for the "embed_batch was dead code" gap.
  - `search_places` returns `[]` on a qdrant client exception.
  - `search_places` returns `[]` when embeddings return `[]`, without calling qdrant search.
  - `search_places` verifies the `destination_id` filter is present in the qdrant call.
  - ★ NEW `count_indexed` returns Qdrant's `count()` result, not a locally-tracked tally.

- `tests/places/test_place_enrichment.py`
  - `enrich_place` skips when `place.summary` is already set.
  - `enrich_place` filters tags to the controlled vocab.
  - `enrich_place` returns `None` on `WandrLLMError`.
  - ★ NEW `enrich_place` returns `None` on malformed/non-JSON LLM output (distinct from the
    `WandrLLMError` case above — both must be tested separately).
  - ★ NEW `enrich_place` persists an empty `enriched_tags` list as success when the LLM
    returns tags that don't match the vocab (not treated as a failure).
  - ★ NEW `enrich_place` never writes to `place.tags` under any code path.

- `tests/scripts/test_p3_scripts.py`
  - `enrich_places` batch continues when one place's `_call_llm_and_parse` returns `None`.
  - ★ NEW `enrich_places` batch continues when one place's *DB write* raises mid-batch —
    this is the real regression test for the `begin_nested()` fix. Construct it so that,
    WITHOUT the savepoint, the second and third places would also fail (simulate by
    patching `PlaceRepository.update` to raise on call #2 only using a real test DB session,
    not a mock, so Postgres's actual transaction-abort behavior is exercised) — assert all
    of calls #1 and #3 still succeed.
  - ★ NEW `enrich_places` never calls `.limit(0)` — regression test asserting the SQL
    statement has no `LIMIT 0` clause when `limit=0` is passed.
  - `index_places` batch continues when one place's embedding is empty.
  - ★ NEW `index_places` uses `upsert_places_batch` (asserts call count is `ceil(N/batch_size)`,
    not `N`).
  - ★ NEW `index_places` sets `indexed_count` from `count_indexed()`, not from the run's
    local success tally — construct a scenario where a `--limit`-bounded run's tally would
    differ from the ground truth and assert the persisted value matches the ground truth.

- `tests/destinations/test_readiness_integration.py` ★ NEW
  - `get_readiness` reaches `tier="ready"` when `is_qdrant_available()` is True and
    `enriched_count`/`indexed_count` are high relative to `place_count` — the direct
    end-to-end proof that P3 closes the tier-progression gap left open by P2.
  - `get_readiness` degrades `indexed_pct` to `0.0` (not an error) when
    `is_qdrant_available()` is False, even with high `indexed_count` in the DB — proves the
    live flag genuinely gates the indexed term, not just the DB counter.
  - ★ Use a gated fixture (place+enriched alone score < 0.7) when asserting a non-ready tier
    on Qdrant-down — high place+enriched fixtures can still be `ready` without indexed under
    the locked P2 formula; do not assert `limited`/`sparse` on those.

Mocking guidance:
- Patch `src.places.service.chat_completion` to return deterministic JSON strings (or
  deliberately malformed strings, for the new malformed-output tests).
- Patch `src.search.places_index.get_qdrant_client`, `.embed_text`, `.embed_batch`, and
  `.is_qdrant_available` — never patch a raw boolean import.
- For the `begin_nested()` regression test specifically, use a real `db_session` fixture
  (not an `AsyncMock`) so Postgres's actual transaction-abort behavior is what's being
  tested — a mocked session can't reproduce this bug class at all.

---

## P3 Complete — Full Verification Checklist (v2)

Before updating `docs/context.md` to claim P3 completion:

```bash
docker compose up -d
python scripts/test_p2_smoke.py

# ── Migration ──
alembic upgrade head
docker exec wandr_postgres psql -U wandr -d wandr -c "\d places"
# Expected: both 'tags' and 'enriched_tags' columns present, distinct types (jsonb dict vs jsonb list)

# ── Qdrant collection + embedding model (lifespan-driven, bounded) ──
python -c "
import asyncio
from src.search.client import ensure_places_collection, is_qdrant_available
from src.search.embeddings import ensure_embedding_model_loaded, is_embeddings_available
async def main():
    await ensure_places_collection()
    await ensure_embedding_model_loaded()
    print('Qdrant available:', is_qdrant_available())
    print('Embeddings available:', is_embeddings_available())
asyncio.run(main())
"

# ── Seed -> enrich -> index -> readiness, end to end ──
python scripts/seed_destination.py --destination "Darjeeling" --radius 30
python scripts/enrich_places.py --destination "Darjeeling" --limit 0
python scripts/index_places.py --destination "Darjeeling" --limit 0

# ── v2: the readiness endpoint must now be able to reach tier=ready — the key proof P3 exists ──
curl -s "http://localhost:8000/api/v1/destinations/{DESTINATION_ID}/readiness" | python -m json.tool
# Expected: tier no longer permanently capped at "limited"

# ── Tests ──
python -m pytest tests/ -v

# ── Import guards (v2 additions) ──
# qdrant_client only in search/client.py and search/places_index.py:
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "import qdrant_client|from qdrant_client" | Where-Object { $_.Path -notmatch "search\\(client|places_index)\.py" }
# Expected: zero results

# sentence_transformers only in search/embeddings.py:
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "sentence_transformers" | Where-Object { $_.Path -notmatch "search\\embeddings\.py" }
# Expected: zero results

# no raw availability-flag imports anywhere (must always go through the function):
Get-ChildItem -Path src -Recurse -Filter *.py | Select-String "import search_available|import _embeddings_available|import _qdrant_available"
# Expected: zero results

# no `.limit(0)` anywhere in the codebase:
Get-ChildItem -Path src,scripts -Recurse -Filter *.py | Select-String "\.limit\(0\)"
# Expected: zero results

# at least one begin_nested() in the batch scripts (savepoint isolation present):
Get-ChildItem -Path scripts -Recurse -Filter *.py | Select-String "begin_nested"
# Expected: at least 1 match (enrich_places.py)

echo "P3 COMPLETE — proceed to P4"
```

### P3 ship criteria (v2)

| Check | Expected |
|-------|----------|
| `places.enriched_tags` column | Present, distinct from `tags`, both correctly typed |
| Qdrant client | `AsyncQdrantClient`, never sync `QdrantClient` |
| `is_qdrant_available()` / `is_embeddings_available()` | Live functions, no raw boolean imports anywhere |
| `embed_text`/`embed_batch` | Thread-offloaded; `embed_batch` returns parallel arrays even when degraded |
| `enrich_place` | Handles `WandrLLMError` AND malformed-JSON as distinct logged failure modes; never writes `place.tags` |
| Batch DB writes | Per-item `session.begin_nested()`; proven via a real-session regression test |
| `upsert_places_batch` | Used by `index_places.py`; one Qdrant call per chunk, not per place |
| `Destination.indexed_count` | Ground truth from `count_indexed()`, not a run tally |
| `--limit 0` | Means unlimited everywhere; `.limit(0)` never called |
| `/destinations/{id}/readiness` | Can now reach `tier=ready` after enrichment + indexing — was permanently capped at `limited` in P2 |
| pytest | All pass, including every ★ NEW regression test above |