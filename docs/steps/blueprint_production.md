# Wandr — Production deploy blueprint (VPS + hosted services)

> **Scope:** Backend API on a VPS. Postgres/PostGIS, Qdrant, Redis, chat LLM, and place embeddings are **hosted** (env URLs/keys).  
> **Not in scope:** workers/queues, self-hosted DB/Qdrant/Redis on the box, frontend hosting, multi-worker scale-out.  
> **Dev infra:** root `docker-compose.yml` (PostGIS + Qdrant + Redis + API) is **local development only** — never use it as the production data plane.

**OpenSpec change:** `production-vps-hosted`  
**Image:** `Dockerfile` + `requirements-prod.txt` (no MiniLM/torch)  
**Optional VPS compose:** `docker-compose.prod.yml` (api + Caddy only)

---

## Topology

```
                    HTTPS api.<domain>
                            │
┌───────────────────────────┼───────────────────────────┐
│  Oracle VPS               ▼                           │
│                 ┌─────────────────┐                   │
│                 │ Caddy / nginx   │  TLS + SSE flush  │
│                 └────────┬────────┘                   │
│                          │                            │
│                 ┌────────▼────────┐                   │
│                 │ wandr-api       │  uvicorn --workers 1│
│                 │ (Docker)        │                   │
└────────────┬────┴─────┬──────────┴─────┬──────────────┘
             │          │                │
             ▼          ▼                ▼
      Hosted PostGIS  Qdrant Cloud   Hosted Redis
      (Neon/…)                       (Upstash/…)
             │
             ▼
      LiteLLM: chat (LLM_*) + Gemini embeddings (GEMINI_API_KEY)
      Public geo: Nominatim / Overpass / OSRM (override via env later)
```

---

## Non-goals (do not add during this deploy)

- Redis/Celery/arq workers or moving planner off the API process  
- Running Postgres, Qdrant, or Redis containers on the VPS  
- Baking MiniLM into the image (prod uses **hosted** embeddings)  
- Frontend / same-domain app UI (API + OAuth callback only for now)

---

## 1. Presetup — accounts & APIs to create

| # | Service | Create | Paste into env |
|---|---------|--------|----------------|
| 1 | **PostGIS host** (Neon / Supabase / …) | Project + database with **PostGIS** enabled; async-friendly connection string | `DATABASE_URL` (`postgresql+asyncpg://…`) |
| 2 | **Qdrant Cloud** | Cluster URL + API key | `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_PLACES_COLLECTION` |
| 3 | **Redis** (Upstash / …) | Redis URL (`rediss://` if TLS) | `REDIS_URL` |
| 4 | **Chat LLM** | Provider API key (NIM / Groq / Gemini chat / …) | `LLM_MODEL`, `LLM_API_KEY`, `LLM_API_BASE` (if needed) |
| 5 | **Gemini embeddings** | Google AI Studio / Gemini API key | `GEMINI_API_KEY`; model in `PLACES_EMBEDDING_MODEL` |
| 6 | **Google OAuth** | Web client; authorized redirect URI | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| 7 | **DNS + TLS** | A/AAAA → VPS public IP; hostname for API | Caddy `WANDR_API_HOST` / server_name; CORS + OAuth host |
| 8 | (Optional) Langfuse | Public/secret keys | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` |

---

## 2. Env vars to populate (production)

Create `.env.production` on the VPS (never commit secrets).

| Variable | Prod value |
|----------|------------|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |
| `SECRET_KEY` | strong random string |
| `DATABASE_URL` | hosted PostGIS `postgresql+asyncpg://…` |
| `QDRANT_URL` | Qdrant Cloud URL |
| `QDRANT_API_KEY` | Qdrant Cloud key |
| `QDRANT_PLACES_COLLECTION` | e.g. `places` or `places_v2` after dim cutover |
| `PLACES_EMBEDDING_BACKEND` | `hosted` |
| `PLACES_EMBEDDING_MODEL` | `gemini/text-embedding-004` |
| `PLACES_EMBEDDING_DIM` | `768` (must match model + collection) |
| `GEMINI_API_KEY` | Google AI key for embeddings |
| `REDIS_URL` | hosted Redis URL (non-empty) |
| `LLM_MODEL` / `LLM_API_KEY` / `LLM_API_BASE` | chosen chat provider |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth web client |
| `GOOGLE_REDIRECT_URI` | `https://<api-host>/api/v1/auth/callback` |
| `CORS_ALLOWED_ORIGINS` | JSON list of explicit app origins — **never** `*` with cookies |
| `NOMINATIM_USER_AGENT` | identifiable contact string (OSM policy) |
| Geo URLs | defaults OK for MVP (`NOMINATIM_BASE_URL`, `OVERPASS_API_URL`, `OSRM_BASE_URL`) |

Also see commented block at the bottom of `.env.example`.

**Dev note:** local MiniLM uses `PLACES_EMBEDDING_BACKEND=local`, dim `384`, model `sentence-transformers/all-MiniLM-L6-v2` against root `docker-compose.yml` (`docker compose up --build` starts PostGIS, Qdrant, Redis, and the API). That compose file is still **not** the VPS data plane.

---

## 3. Build & run API on the VPS

```bash
# On a machine with Docker (build locally or on VPS)
docker build -t wandr-api:prod -f Dockerfile .

# Or compose (api + Caddy):
# 1) Copy .env.production and set WANDR_API_HOST in Caddy env / file
# 2) Edit deploy/Caddyfile hostname
docker compose -f docker-compose.prod.yml up -d --build
```

Default process: `uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1`.

**Proxy / SSE:** Caddy (`deploy/Caddyfile`) uses `flush_interval -1` on `/api/v1/planner/generate`. Nginx example: `deploy/nginx.conf.example` with `proxy_buffering off`.

---

## 4. Migrate DB (not in app lifespan)

Against **hosted** `DATABASE_URL`:

```bash
# Example: one-off container with same image + env
docker run --rm --env-file .env.production wandr-api:prod \
  alembic upgrade head
```

(If the image `PATH`/working dir needs `PYTHONPATH=/app`, it is already set in the Dockerfile.)

---

## 5. Qdrant dim cutover + reindex (**BREAKING**)

Local/dev MiniLM vectors are **384-d**. Hosted Gemini `text-embedding-004` uses **768-d**. Do **not** query a 384 collection with 768 vectors.

**Preferred:** new collection name (e.g. `places_v2`), set `QDRANT_PLACES_COLLECTION=places_v2`, keep old collection until verified.

1. App lifespan `ensure_places_collection()` creates collection at `PLACES_EMBEDDING_DIM` if missing.  
2. With prod env (`hosted` + dim 768), run index:

```bash
docker run --rm --env-file .env.production wandr-api:prod \
  python scripts/index_places.py --destination "Darjeeling" --limit 0
```

Repeat per destination (or your batch process). Enrich first if summaries/tags missing (`scripts/enrich_places.py`).

---

## 6. Google OAuth + CORS

- OAuth redirect: `https://<api-host>/api/v1/auth/callback` in Google Cloud Console **and** `GOOGLE_REDIRECT_URI`.  
- Cookies stay `SameSite=Lax` (MVP Option A) — when a frontend exists, put it on the **same registrable domain** as the API.  
- `CORS_ALLOWED_ORIGINS` must list explicit HTTPS origins (JSON array).

---

## 7. Smoke checklist

1. `GET https://<api-host>/api/v1/health` → 200  
2. `GET /api/v1/destinations/search?q=…` (rate-limited)  
3. Destination readiness shows search available when Qdrant + embeddings OK  
4. `POST /api/v1/planner/generate` SSE streams events (proxy not buffering)  
5. Optional: Google login round-trip if OAuth configured  

---

## Quick reference — repo files

| File | Role |
|------|------|
| `Dockerfile` | Prod API image |
| `requirements-prod.txt` | Prod deps (no sentence-transformers) |
| `docker-compose.prod.yml` | VPS: api + Caddy |
| `docker-compose.yml` | **Dev only** PostGIS + Qdrant + Redis + API |
| `deploy/Caddyfile` | TLS + SSE flush |
| `deploy/nginx.conf.example` | Nginx SSE alternative |
| `.env.example` | Dev defaults + commented prod checklist |
