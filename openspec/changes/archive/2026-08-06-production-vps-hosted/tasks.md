## 1. Settings and env surface

- [x] 1.1 Add `PLACES_EMBEDDING_BACKEND` (`hosted` | `local`, default `local` for existing dev) and document prod default `hosted` in `.env.example`
- [x] 1.2 Set prod-oriented example values: hosted model `gemini/text-embedding-004`, `PLACES_EMBEDDING_DIM=768`, note MiniLM `384` only for `local`
- [x] 1.3 Ensure Gemini key wiring is documented (`GEMINI_API_KEY` for LiteLLM `gemini/*` embeddings); add any thin settings field only if required — no `os.environ.get` outside settings/LiteLLM norms
- [x] 1.4 Expand `.env.example` with commented **production checklist** block (DATABASE_URL, QDRANT_*, REDIS_URL, LLM_*, embedding backend/model/dim, GOOGLE_*, CORS, SECRET_KEY, NOMINATIM_USER_AGENT)

## 2. Hosted embeddings gateway

- [x] 2.1 Add `embed_texts` (or `embed_text`/`embed_batch` helpers) on `src/core/llm/client.py` using LiteLLM embedding API; timeouts + tenacity; never import litellm outside this module
- [x] 2.2 Refactor `src/search/embeddings.py` to branch on `PLACES_EMBEDDING_BACKEND`: hosted → gateway; local → existing SentenceTransformer + `to_thread`
- [x] 2.3 Hosted `ensure_embedding_model_loaded()`: no SentenceTransformer; fail-soft availability; lifespan in `main.py` unchanged call sites
- [x] 2.4 Preserve fail-soft contracts: unavailable/`[]` and batch parallel-array `[[]…]`; vector length = `PLACES_EMBEDDING_DIM`
- [x] 2.5 Update/add unit tests for hosted path (mock gateway) and keep local path tests green

## 3. Production packaging

- [x] 3.1 Add production `Dockerfile` (API only; prod deps without torch/sentence-transformers when hosted-only install path is used — e.g. `requirements-prod.txt` or equivalent)
- [x] 3.2 Default CMD: `uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1`
- [x] 3.3 Optional `docker-compose.prod.yml` (or `deploy/`) with `api` + Caddy/nginx only — no PostGIS/Qdrant/Redis services
- [x] 3.4 Add proxy example config with TLS and **SSE non-buffering** for `/api/v1/planner/generate`
- [x] 3.5 Add `.dockerignore` so build context excludes `.env`, local data, tests junk as appropriate

## 4. Operator blueprint (human SOP)

- [x] 4.1 Write `docs/steps/blueprint_production.md`: topology diagram, non-goals, ordered presetup → deploy → smoke
- [x] 4.2 Include full **accounts/API to create** table and **env vars to populate** table (from design checklist)
- [x] 4.3 Document migrate (`alembic upgrade head`), Qdrant dim cutover (new collection name preferred), `index_places` reindex with hosted embeddings
- [x] 4.4 Document Google OAuth redirect `https://<api-host>/api/v1/auth/callback` and CORS explicit origins
- [x] 4.5 State clearly: root `docker-compose.yml` is **dev-only**

## 5. Verification and context

- [x] 5.1 Prove locally: hosted backend mocked/unit; optional live Gemini embed smoke if key present (skip if unset)
- [x] 5.2 Prove Docker build of prod image succeeds without pulling MiniLM
- [x] 5.3 Update `docs/context.md` (Last updated, next step/production note, deployment stubs cleared once packaging lands)
- [x] 5.4 Spot-check AGENT.md: no litellm outside `core/llm`; all new env via `get_settings()`
