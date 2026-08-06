## Why

P7 backend is feature-complete for MVP, but there is no production packaging path: the API still assumes local Docker PostGIS/Qdrant and in-process MiniLM (`sentence-transformers` + torch), which is too heavy for a small Oracle VPS and blocks an easy “API on VPS, everything else hosted” deploy. We need a clean presetup + deploy blueprint now — backend container only, hosted data/LLM/embeddings via env — without inventing workers, queues, or self-hosted infra.

## What Changes

- Add a **production deployment blueprint** (step-by-step presetup, Dockerize API, reverse proxy/SSE, migrate, reindex, smoke) under `docs/steps/blueprint_production.md`, aligned with this change.
- Package the API for VPS: production **Dockerfile** (slim runtime; **no** local MiniLM/torch in the prod image), optional VPS compose for **API + TLS proxy only** (local `docker-compose.yml` stays PostGIS+Qdrant for **dev only**).
- Switch place embeddings to **hosted Gemini** via LiteLLM through `src/core/llm/client.py` (**BREAKING** for existing Qdrant vectors: default dim moves MiniLM **384 → Gemini embedding dim, typically 768**; collection recreate + full `index_places` reindex required).
- Keep `embed_text` / `embed_batch` / fail-soft contracts in `src/search/embeddings.py`; lifespan no longer loads a local SentenceTransformer when the hosted backend is selected.
- Add settings + `.env.example` / prod env template covering all hosted URLs, API keys, OAuth redirect, CORS, Redis, embedding model/dim.
- Document the **external accounts and env values operators must populate** before first deploy (PostGIS host, Qdrant Cloud, Redis, LLM, Gemini embeddings, Google OAuth, domain/TLS).

### Non-goals

- Background Redis/Celery workers or moving planner off the API process
- Self-hosting Postgres, Qdrant, Redis, OSRM, or embeddings on the VPS
- Frontend hosting / same-domain UI app (API + OAuth callback domain only for now)
- Multi-worker uvicorn, autoscaling, or lighter-than-Gemini embedding vendor shopping
- Changing planner/chat LLM provider logic beyond env (already LiteLLM-swappable)

## Capabilities

### New Capabilities

- `production-deployment-blueprint`: Operator-facing step-by-step presetup and VPS deploy contract (hosted services, Docker API image, proxy/SSE, migrate/reindex/smoke, env & API checklist).
- `production-runtime-packaging`: Production Dockerfile / VPS-only compose surface; prod image MUST NOT require local sentence-transformers/torch; single uvicorn worker default for small VPS.
- `hosted-embeddings-gateway`: Hosted Gemini embeddings via `core/llm` LiteLLM `embedding()`; settings-driven model/dim; search layer keeps fail-soft `embed_*` API; **BREAKING** Qdrant dim/reindex.

### Modified Capabilities

- `p3-place-knowledge-layer`: Embedding backend is no longer hard-locked to local MiniLM-only; production path uses hosted embeddings with configurable `PLACES_EMBEDDING_DIM` matching the hosted model.

## Impact

- **Code:** `src/core/llm/client.py` (add embedding gateway), `src/search/embeddings.py`, `src/config.py`, `src/main.py` lifespan, tests under `tests/search/` / LLM mocks; optional remove or gate `sentence-transformers` for prod deps.
- **Data:** Existing Qdrant `places` collections at 384d are incompatible — recreate collection at new dim and reindex.
- **Ops:** Hosted PostGIS (Neon/Supabase/etc with PostGIS), Qdrant Cloud, Upstash (or equivalent) Redis, Gemini API key for embeddings, chat LLM keys, Google OAuth client with prod redirect URI, DNS + TLS on VPS.
- **AGENT.md:** litellm remains only inside `core/llm/client.py`; all new env via `get_settings()`.
- **Docs:** `docs/steps/blueprint_production.md` becomes the human deploy SOP; `docs/context.md` updated when apply is validated.
