# Wandr — Production deploy blueprint (VPS + hosted services)

> **Scope:** Backend API on a VPS. Postgres/PostGIS, Qdrant, Redis, chat LLM, and place embeddings are **hosted** (env URLs/keys).  
> **Not in scope:** workers/queues, self-hosted DB/Qdrant/Redis on the box, frontend hosting, multi-worker scale-out.  
> **Dev infra:** root `docker-compose.yml` (PostGIS + Qdrant + Redis + API) is **local development only** — never use it as the production data plane.

**OpenSpec change:** `production-vps-deploy`  
**Image:** `Dockerfile` + `requirements-prod.txt` (no MiniLM/torch)  
**Compose:** `docker-compose.prod.yml` (api + Caddy only)  
**Env template:** `.env.production.example` → copy to `.env.production` on VPS (never commit)  
**Ops:** `ops/migrate.sh` → `ops/deploy.sh` → `ops/health.sh` (see §3)

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

Create `.env.production` on the VPS from `.env.production.example` (never commit secrets).

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
| `NOMINATIM_USER_AGENT` | **Real contact email** in the string (OSM policy). Never `contact@example.com` |
| `NOMINATIM_BASE_URL` / `NOMINATIM_API_KEY` | Default public OSM often **403s from cloud/VPS IPs**. If blocked after a real UA, point `NOMINATIM_BASE_URL` at a Nominatim-compatible free-tier provider and set `NOMINATIM_API_KEY` |
| `OVERPASS_API_URL` / `PLACES_SOURCES` | Public Overpass may 4xx from datacenters — set a mirror or prefer `opentripmap,geoapify` (free keys) |
| `OSRM_BASE_URL` | public default OK for MVP |

Also see `.env.production.example` (committed template with correct Settings field names).

**Geo troubleshooting:** `GET /destinations/search` returning **502** `external_service_error` (service=`nominatim`) means the geocoder upstream rejected the request — fix UA or swap provider. **404** `not_found` means a true miss (or geocode timeout). Empty places after search works → check Overpass / `PLACES_SOURCES` + free API keys.

**Dev note:** local MiniLM uses `PLACES_EMBEDDING_BACKEND=local`, dim `384`, model `sentence-transformers/all-MiniLM-L6-v2` against root `docker-compose.yml` (`docker compose up --build` starts PostGIS, Qdrant, Redis, and the API). That compose file is still **not** the VPS data plane.

---

## 3. Build & run API on the VPS

**First deploy order (hosted data plane):**

1. Copy `.env.production.example` → `.env.production`; fill secrets; set `WANDR_API_HOST` and `WANDR_GHCR_OWNER`.
2. `ops/migrate.sh` — Alembic against hosted `DATABASE_URL`.
3. §5 Qdrant dim cutover + `scripts/index_places.py` if moving from local MiniLM 384 → hosted 768.
4. `ops/deploy.sh [sha]` — pull GHCR image (or local `wandr-api:prod`) and `compose up -d`.
5. `ops/health.sh` — `GET /api/v1/health` over HTTPS.
6. Planner SSE smoke (§7).

```bash
# Build image off the 1GB VPS (laptop or CI), not on the box:
docker build -t wandr-api:prod -f Dockerfile .

# Or GHCR image from .github/workflows/deploy.yml (workflow_dispatch)

# On VPS after .env.production is ready:
./ops/migrate.sh
./ops/deploy.sh          # or ./ops/deploy.sh <git-sha> after CI push
./ops/health.sh
```

Default process: `uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1`.

**Proxy / SSE:** Caddy (`deploy/Caddyfile`) uses `flush_interval -1` on `/api/v1/planner/generate`. Nginx example: `deploy/nginx.conf.example` with `proxy_buffering off`.

---

## 4. Migrate DB (not in app lifespan)

Prefer `ops/migrate.sh`. Equivalent one-off:

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
| `.env.production.example` | Committed prod env template (no secrets) |
| `ops/*.sh` | migrate, deploy, health, status, logs, rollback, backup |
| `deploy/Caddyfile` | TLS + SSE flush |
| `deploy/nginx.conf.example` | Nginx SSE alternative |
| `.env.example` | Dev defaults + commented prod checklist |
