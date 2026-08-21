# Issue: destination search `ERR_EMPTY_RESPONSE` (Chrome)

**Status:** Permanent fix via OpenSpec `fix-search-empty-response`  
**Last updated:** 2026-08-21  
**Scope:** `guideagent` only (sibling Next.js timeout unchanged)

---

## Symptom

API is up (`GET /api/v1/health` 200) but the sibling FE console shows:

```text
GET http://localhost:8000/api/v1/destinations/search?q=dhaka net::ERR_EMPTY_RESPONSE
```

Same for other cache-miss / in-flight queries (`q=ba`, `q=barlin`). This is **not** `ERR_CONNECTION_REFUSED` (nothing listening on `:8000`).

## Root cause

Chrome `ERR_EMPTY_RESPONSE` means the TCP connection closed with no HTTP status. Two overlapping causes:

1. **Nominatim cache-aside vs FE abort.** Search is DB ILIKE first, then `geocode()`. httpx read timeout 10s × 3 retries plus 1 req/s throttle can exceed the FE `fetch` 20s abort. Abort + worker restart looks like an empty response, not JSON 404.
2. **Compose `uvicorn --reload` watching `/app`.** WatchFiles on the whole cwd plus Windows bind-mounts can restart the worker mid-request.

Cached names (e.g. Darjeeling) return in milliseconds and usually look fine.

## Permanent solution

| Layer | Behavior |
|-------|----------|
| Search | `asyncio.wait_for(geocode(...), SEARCH_GEOCODE_TIMEOUT_SECONDS)` (default 8s). Timeout → 404 `not_found`, same as a Nominatim miss |
| Compose | `uvicorn --reload --reload-dir /app/src` — reload still works for application source, not the entire `/app` tree |

OpenSpec: `openspec/changes/fix-search-empty-response/`

### Operator check

```bash
curl -s -o NUL -w "%{http_code}" "http://127.0.0.1:8000/api/v1/destinations/search?q=dhaka"
```

Expect `200` or `404`, never a dropped connection.

If health itself fails, see **API boot failure** below.

---

# Issue: API boot failure → destination search “network” error

**Status:** Permanent compose fix via OpenSpec `survive-compose-restart-api-boot` (builds on `allow-catalog-boot-without-llm-key`)  
**Last updated:** 2026-08-21  
**Scope:** `guideagent` only (sibling Next.js unchanged)

---

## Symptom

With Compose “running” or after `docker compose down` / `up`:

- Sibling FE destination search (`q=darjeeling`) fails — empty results / browser `net::ERR_CONNECTION_REFUSED` on `http://localhost:8000/api/v1/destinations/search`.
- Postgres, Qdrant, Redis may look healthy while `wandr_api` is missing or still starting.
- Unused Next.js font preload warnings are unrelated.

## Root cause (two layers)

Not a frontend URL bug. `NEXT_PUBLIC_API_URL=http://localhost:8000` is correct.

1. **LLM key used to block boot.** Alembic + uvicorn call `get_settings()`. `LLM_API_KEY` was required. A commented/empty gitignored `.env` exited `wandr_api` with code 1. Catalog routes never call the LLM but could not start. Fixed in `allow-catalog-boot-without-llm-key` (`LLM_API_KEY` defaults to `""`; gateway raises `llm_unavailable` when generate/enrich need a key).

2. **Compose recreate did not keep Settings pointed at the host `.env`.** Settings loads `env_file=".env"` from the container cwd (`/app/.env`). That path was **not** bind-mounted. After `docker compose down` then `up`, the container only saw secrets if Compose `env_file` injection worked. Pasting keys into `.env` by hand was temporary and looked like “the fix disappeared” on the next down/up.

`docker compose down` **always** unbinds `:8000` until `up` finishes. That window is expected; it is not a lost code change.

## Permanent solution

| Layer | Behavior |
|-------|----------|
| Settings | `LLM_API_KEY` still optional at boot (`""`) |
| LLM gateway | Empty key → `WandrLLMError` (`llm_unavailable`) before LiteLLM |
| Compose `api` | Bind-mount `./.env:/app/.env:ro` so `get_settings()` reads the host file after every recreate |
| Compose `environment` | Still overrides `DATABASE_URL` / `QDRANT_URL` / `REDIS_URL` to Docker DNS (host `.env` `localhost:5433` must not win inside the container) |
| Compose `env_file` | Still injects process env as a second path |
| Restart policy | `unless-stopped` on local services (Docker Desktop reboot). Does **not** replace an explicit `compose down` — run `up` again |

OpenSpec: `openspec/changes/survive-compose-restart-api-boot/`  
Prior: `openspec/changes/allow-catalog-boot-without-llm-key/`

### Non-goals

- No new endpoints or env var names
- No FE / CORS / cookie changes
- Do not commit `.env` or real secrets (`.dockerignore` still excludes `.env` from the image)
- Do not make `DATABASE_URL` / `SECRET_KEY` / `NOMINATIM_USER_AGENT` optional

## Proof (must include a down → up cycle)

```bash
# from guideagent/
docker compose down
docker compose up -d
docker compose ps   # wait until wandr_api healthy (MiniLM lifespan can take up to ~2 min)
curl -s http://localhost:8000/api/v1/health
curl -s "http://localhost:8000/api/v1/destinations/search?q=darjeeling"
docker compose exec api test -f /app/.env
```

Generate still requires a real `LLM_API_KEY` in **`guideagent/.env`** (API env, not the Next app).

## Operator checklist if search fails again

1. `docker compose ps` — is `wandr_api` Up/healthy? If you just ran `down`, run `up` and wait.
2. `docker logs wandr_api` — missing `DATABASE_URL` / `SECRET_KEY` / `NOMINATIM_USER_AGENT`?
3. Confirm `guideagent/.env` exists (Compose mounts it at `/app/.env`). Copy from `.env.example` if needed.
4. Confirm FE uses `NEXT_PUBLIC_API_URL=http://localhost:8000`.
5. For **generate** only: nonempty `LLM_API_KEY` in `guideagent/.env`, then recreate `api`.

---

# Issue: generate SSE `generation_aborted` (“Generation failed”)

**Status:** Permanent fix via OpenSpec `fix-generation-aborted-empty-itinerary`  
**Last updated:** 2026-08-21  
**Scope:** `guideagent` planner (sibling Next.js already mapped SSE `error` correctly)

---

## Symptom

API health and destination search succeed. Guest generate on a ready destination (Darjeeling `458854b1-4d2a-4d02-8901-e26ed59c0c8b`, 132 places) streams SSE then the FE shows:

```text
Generation failed
generation_aborted
```

This is **not** `generation_timeout`, **not** HTTP 409 `destination_not_ready`, and **not** a missing Next.js LLM key.

## Root cause

`generation_aborted` is the cold-path fallback when the graph returns without `needs_clarification` and without (`plan_complete` + a schedule with stops).

Live trace before the fix:

1. `chat_with_tools` against the configured NVIDIA NIM model failed (`llm_retry_count=12`, LiteLLM debug lines). Preference JSON parse still produced defaults.
2. The agent synthesized a **static** DISCOVER default: `check_readiness` every cycle.
3. Stuck detector (`PLANNER_AGENT_PHASE_STUCK_LIMIT`, host `.env` may be `2`) auto-advanced DISCOVER→PLAN with **zero** `candidate_pois`.
4. `build_route` returned `ok=True` for an empty ranked set (~0.09ms, empty day shells).
5. `validate_itinerary` failed `empty_itinerary`; `finish_plan` ran; SSE terminal `error` / `generation_aborted`.

Eval row: `candidates_retrieved=0`, `abort_triggered=true`. The FE panel was contract-correct.

## Permanent solution

| Layer | Behavior |
|-------|----------|
| Agent default | State-aware: DISCOVER `check_readiness` → `search_places` → `rank_places`; PLAN `build_route` then `build_schedule` |
| Stuck detector | DISCOVER with no candidates, or PLAN with no usable schedule → WRAP_UP abort (`phase_stuck*`), **not** fake-advance into an empty later phase |
| `build_route` | Empty ranked **and** candidates → `ok=False`, `code=no_ranked_places` |

Structure still comes from search/rank + `travel_engine`, not from the LLM. NVIDIA NIM tool-calling is **not** required for a usable itinerary.

OpenSpec: `openspec/changes/fix-generation-aborted-empty-itinerary/`

### Non-goals

- No FE abort-timeout, CORS, or cookie changes
- No new endpoints or env vars
- Do not “fix” by only raising `PLANNER_GENERATION_TIMEOUT_SECONDS`

## Proof (Compose already up after operator `down`)

```bash
# from guideagent/ — stack was down; bring it up and wait until wandr_api healthy
docker compose up -d
curl -s http://127.0.0.1:8000/api/v1/health
curl -s "http://127.0.0.1:8000/api/v1/destinations/search?q=darjeeling"
```

POST `/api/v1/planner/generate` with `destination_id=458854b1-4d2a-4d02-8901-e26ed59c0c8b` MUST include `tool_done` `search_places` then terminal `itinerary_done` with `trip_id`.

Live (2026-08-21): curl → `itinerary_done` + `trip_id` `ca403250-4917-41a0-bec6-3918725e8eb4`. Browser guest generate → `/trips/474314b8-1b01-43d0-bd11-a40b54892329` with Day 1–3 stops (not the “Generation failed” panel).

Pytest: `python -m pytest tests/planner -q` (65 passed).

### Operator checklist if generate shows generation_aborted again

1. `docker compose ps` — `wandr_api` healthy? Search still 200?
2. SSE `tool_done` names — is `search_places` missing? Then the default-tool patch is not loaded (restart `api` after pull).
3. If `search_places` ran and still abort: destination places / Qdrant index / travel_engine validation — not the empty-skip path.
4. `generation_timeout` is a different code (graph ceiling). Do not confuse with `generation_aborted`.
