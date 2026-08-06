## Context

Wandr P7 backend is complete for MVP. Local dev uses `docker compose` (PostGIS + Qdrant) and in-process MiniLM via `sentence-transformers`. Production intent (blueprint + this change): **API on a small Oracle VPS**; Postgres/PostGIS, Qdrant, Redis, chat LLM, and **place embeddings** are **hosted** and injected by env. Chat already goes through LiteLLM in `src/core/llm/client.py`; embeddings do not yet — they load MiniLM at lifespan and dominate image size/RAM.

Human SOP lands in `docs/steps/blueprint_production.md`. OpenSpec artifacts are the contract for apply.

## Goals / Non-Goals

**Goals:**

- Step-by-step presetup + deploy blueprint operators can follow once.
- Slim production Docker image (API only; no torch/MiniLM in prod runtime).
- Hosted Gemini embeddings through the LLM gateway; keep `embed_text` / `embed_batch` fail-soft contracts.
- Complete env + external API checklist (what to create, what to paste).
- VPS runs: TLS reverse proxy + single uvicorn worker API container.

**Non-Goals:**

- Workers/queues; self-hosted DB/Qdrant/Redis/OSRM; frontend deploy; multi-worker scale-out.

## Decisions

### D1 — Topology: API on VPS, data plane hosted

| Layer | Choice | Why |
|-------|--------|-----|
| API | Docker on Oracle VPS | Controllable deploy; SSE-friendly |
| Postgres+PostGIS | Neon / Supabase / equivalent | Blueprint prod mapping; PostGIS required |
| Qdrant | Qdrant Cloud | Already client-based |
| Redis | Upstash (or equivalent) | Rate limit + planner cache; tiny VPS RAM |
| Chat LLM | Existing `LLM_*` env | Already provider-swappable |
| Embeddings | Hosted Gemini via LiteLLM | Slim image; fits “everything hosted” |
| Geo | Public Nominatim / Overpass / OSRM URLs | OK for MVP; override later via env |

**Alternatives:** All-in-one VPS — rejected (1GB RAM + PostGIS + Qdrant + torch fails). Bake MiniLM only — rejected (torch still fat; user chose hosted embeddings).

### D2 — Embeddings: gateway + settings, not MiniLM in prod

```
search/embeddings.py  →  core/llm/client.embed_*  →  litellm.aembedding / embedding
                              ↑
                     PLACES_EMBEDDING_BACKEND=hosted
                     PLACES_EMBEDDING_MODEL=gemini/text-embedding-004
                     PLACES_EMBEDDING_DIM=768
```

- **Hosted (prod default):** `ensure_embedding_model_loaded()` validates config / optional ping; sets `embeddings_available` without loading SentenceTransformer.
- **Local (dev optional):** keep MiniLM path behind `PLACES_EMBEDDING_BACKEND=local` so offline pytest can stay; prod image MUST NOT install sentence-transformers/torch.
- LiteLLM **only** inside `core/llm/client.py` (AGENT.md).
- Resilience: explicit timeouts; tenacity retries consistent with LLM client; on failure → `[]` / parallel `[[]]` (same as today). Never raise to callers.
- **BREAKING:** existing 384d Qdrant points invalid → new collection size = `PLACES_EMBEDDING_DIM` (768 for `text-embedding-004`) + full reindex.

**Alternatives:** Call Gemini SDK from `search/` — rejected (bypasses gateway). Keep MiniLM in prod image “just in case” — rejected (defeats slim VPS).

### D3 — Packaging

- **Dockerfile (prod):** multi-stage optional; runtime deps without torch; `CMD` uvicorn `src.main:app --host 0.0.0.0 --port 8000 --workers 1`.
- **VPS compose (optional):** `api` + `caddy`/`nginx` only — never ship PostGIS/Qdrant in prod compose.
- **Dev compose:** unchanged (`docker-compose.yml` local infra only).
- Proxy: TLS; **disable buffering** for `POST /api/v1/planner/generate` (SSE). Prefer Caddy for auto-TLS simplicity unless nginx already preferred.

### D4 — Deploy sequence (operator)

1. Create hosted accounts (see checklist below).
2. Populate prod env file on VPS / secret store.
3. Build & push/pull API image.
4. `alembic upgrade head` against hosted DB (one-off container or CI job — **not** app lifespan).
5. Recreate Qdrant collection at new dim (delete/recreate or new collection name via `QDRANT_PLACES_COLLECTION`).
6. Run `index_places` (and enrich if needed) against prod using hosted embeddings.
7. Start API + proxy; point DNS; update Google OAuth redirect.
8. Smoke: `/api/v1/health`, destinations search, one planner SSE.

### D5 — Docs split

- `docs/steps/blueprint_production.md` — full human checklist + ordered commands.
- OpenSpec design/tasks — engineering apply contract.
- Do not duplicate AGENT.md or full system essays into the blueprint.

## Env & API population checklist

Operators must create/fill these before first prod boot.

### External accounts / APIs to provision

| # | Service | What to create | Paste into |
|---|---------|----------------|------------|
| 1 | PostGIS host (Neon/Supabase/…) | Project + DB with **PostGIS** enabled; connection string | `DATABASE_URL` (`postgresql+asyncpg://…`) |
| 2 | Qdrant Cloud | Cluster URL + API key; empty collection or recreate after dim change | `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_PLACES_COLLECTION` |
| 3 | Redis (Upstash/…) | Redis URL (TLS rediss:// if required) | `REDIS_URL` |
| 4 | Chat LLM | Provider key (NIM / Groq / Gemini chat / …) | `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE` (if needed) |
| 5 | Gemini embeddings | Google AI Studio / Gemini API key | LiteLLM expects `GEMINI_API_KEY` (or map via settings → env for LiteLLM); model id in `PLACES_EMBEDDING_MODEL` |
| 6 | Google OAuth | Web client; authorized redirect = prod callback | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| 7 | Domain + TLS | DNS A/AAAA → VPS; HTTPS on API host | Proxy config; `CORS_ALLOWED_ORIGINS`; OAuth redirect host |
| 8 | (Optional) Langfuse | Keys | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` |

### Application env (prod values)

| Variable | Prod expectation |
|----------|------------------|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | strong random |
| `DATABASE_URL` | hosted PostGIS asyncpg URL |
| `QDRANT_URL` / `QDRANT_API_KEY` / `QDRANT_PLACES_COLLECTION` | cloud |
| `PLACES_EMBEDDING_BACKEND` | `hosted` |
| `PLACES_EMBEDDING_MODEL` | `gemini/text-embedding-004` (or current Gemini embed id) |
| `PLACES_EMBEDDING_DIM` | `768` (must match model + Qdrant collection) |
| `REDIS_URL` | hosted Redis (non-empty for shared limit/cache) |
| `LLM_*` | chosen chat provider |
| `GEMINI_API_KEY` | embeddings (and chat if Gemini chat) |
| `GOOGLE_*` | prod redirect `https://<api-host>/api/v1/auth/callback` |
| `CORS_ALLOWED_ORIGINS` | explicit frontend origins (JSON list; never `*`) |
| `NOMINATIM_USER_AGENT` | identifiable contact string (policy) |
| `NOMINATIM_BASE_URL` / `OVERPASS_API_URL` / `OSRM_BASE_URL` | public defaults OK for MVP |
| Rate-limit / planner bounds | keep defaults unless tuning |

Dev may set `PLACES_EMBEDDING_BACKEND=local` + MiniLM model/dim 384 against local compose.

## Risks / Trade-offs

- [Risk] Gemini embed rate limits / cost on bulk `index_places` → Mitigation: batch + existing script concurrency knobs; retry/fail-soft; run reindex off-peak.
- [Risk] Dim mismatch silently breaks search → Mitigation: collection created with `PLACES_EMBEDDING_DIM`; document recreate+reindex as mandatory; smoke readiness/search after deploy.
- [Risk] 1GB VPS still tight without torch but OS+proxy+Python can spike → Mitigation: `--workers 1`; monitor RSS; bump RAM if OOM.
- [Risk] Public OSRM/Nominatim abuse/limits → Mitigation: acceptable MVP; override URLs later.
- [Risk] OAuth/cookie SameSite without frontend domain → Mitigation: API-only smoke uses redirect URI; document Option A same-registrable-domain when frontend ships.
- [Trade-off] Dual local/hosted embedding backends add settings surface → Worth it so pytest/offline can keep MiniLM without bloating prod image.

## Migration Plan

1. Land code: gateway + settings + Dockerfile + blueprint doc.
2. Stand up hosted services; fill env.
3. Migrate DB (`alembic upgrade head`).
4. Point Qdrant at new dim (new collection name **or** delete+recreate `places`).
5. Reindex all destinations with hosted embeddings.
6. Roll API container; verify health + one SSE generate.
7. **Rollback:** keep previous image tag; revert `PLACES_EMBEDDING_*` only works if Qdrant still has old 384d data — after recreate, rollback requires restoring old collection backup or re-reindex with MiniLM (prefer: don’t delete old collection until new index verified — use a new collection name for cutover).

## Open Questions

- Exact Gemini embedding model id at apply time (`text-embedding-004` vs newer `gemini-embedding-*`) — confirm against LiteLLM docs during implement; dim must match.
- Caddy vs nginx for first VPS — default **Caddy** in blueprint unless operator prefers nginx.
- Whether prod `requirements` split (`requirements.txt` vs `requirements-prod.txt`) or optional extra — decide in tasks for cleanest Docker layer.
