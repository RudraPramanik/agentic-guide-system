## Context

See `proposal.md` for why. Today `DestinationService.search` cache-aside geocodes and upserts a shell (`place_count=0`). Planner `POST /generate` 409s when `place_count < PLANNER_ABSOLUTE_MIN_PLACES`. POI load lives in `scripts/seed_destination.py` (`seed_destination_into` / `_seed_from_geocoded` / `seed_places`) — CLI only. `GET /destinations/search` is 20/min exact-path; UUID routes cannot use `_route_limit_table`. Overpass `read=90s` with `[]` on failure. No job table exists. `get_cache_backend()` is available for short-lived locks.

## Goals / Non-Goals

**Goals:**
- Public `POST /api/v1/destinations/{id}/prepare` that reuses the seed pipeline around the stored point
- 200 if already at floor; 202 + background scrape otherwise; FE polls readiness
- Shared ingest module so CLI and HTTP do not diverge
- IP-keyed prepare rate limit (default 5/min); fail-open
- `docs/FE_guide.md` contract for the sibling Next.js app

**Non-Goals:**
- New Alembic columns or a durable job queue
- Enrich/index on this path
- Changing generate auth, trip list auth, or the place-count floor
- Seeding inside search GET
- Country/region polygons
- Frontend implementation in `guideagent-frontend`

## Decisions

### D1 — New POST on destinations router, not search and not generate

Search stays Nominatim-fast. Generate stays a 409 floor (no scrape inside SSE). Prepare is an explicit step the FE can poll.

**Alternatives:** scrape in search (timeouts, 20/min burns Overpass); scrape in generate (mixes geo into SSE, today’s 409 is pre-stream). Rejected.

### D2 — Kickoff 202 + poll readiness (not a blocking 90s POST)

If `place_count >= PLANNER_ABSOLUTE_MIN_PLACES` → HTTP **200** `status=ready`. Else set a short-lived in-flight lock on `get_cache_backend()`, start `asyncio.create_task` with its **own** `AsyncSessionLocal` (request session must not outlive the response), return HTTP **202** `status=preparing`. Duplicate prepare while locked → 202, no second task. Clear the lock in `finally` after seed commit/failure.

Do **not** add fields to `DestinationReadinessOut`. Completion signal is existing readiness `place_count`.

**Alternatives:** blocking POST (FE default JSON timeout is 20s; proxies may kill 90s); new `prepare_status` column (migration, out of scope). Rejected for MVP.

### D3 — Ingest lives under `src/destinations/`, CLI thins out

Move shared seed loop to something like `src/destinations/ingest.py` (`seed_places`, seed-from-lat/lng or from existing `Destination`). CLI keeps argparse + commit. `DestinationService.prepare` loads dest, skips if at floor, else starts ingest in a background session. Router never imports geo or ingest.

**Alternatives:** `from scripts.seed_destination import …` in the service (layering smell). Rejected.

### D4 — Radius default 30, max 50; body optional

Match CLI default. Cap at 50 km so “country” searches still mean a point + radius, not a national dump. Optional `PrepareIn.radius_km`.

### D5 — Auth None; guest generate unchanged

Prepare is catalog ingest, like search/readiness. No `wandr_session` required to scrape. Generate still `optional_auth` + Set-Cookie; trip GET still session-or-owner.

### D6 — IP-keyed limiter dependency, not path table

UUID path cannot exact-match `_route_limit_table` (same reason trip-edit is a dependency). Settings: `RATE_LIMIT_DESTINATIONS_PREPARE_REQUESTS=5`, `WINDOW_SECONDS=60`. Key `{ip}:dest_prepare`. Fail-open. Dual default 60/min middleware on the UUID path is acceptable.

### D7 — DTO `DestinationPrepareOut`

Fields: `destination_id`, `status` (`ready` | `preparing`), `place_count`. Envelope `ApiResponse`. No SSE. OpenAPI must list 200 and 202.

### D8 — FE_guide.md in this repo

Update §8 destinations matrix, §9 flow (insert prepare + poll), §14 DTO, §16 errors (409 still floor; 202 is not an error; 429 on prepare). State: do not use search as scrape; poll interval ~2s; client timeout ~120s before showing “not enough places”; first sparse poll is not failure. Sibling FE code is a later PR.

### D9 — Resilience (Overpass)

Existing `fetch_pois` retries / `[]` on failure. Empty result → dest remains, `place_count` 0 or previous; lock cleared; FE timeout surfaces the same 409 on generate. No LLM. Nominatim only on search miss, not on prepare.

## Risks / Trade-offs

- [Overpass 504 / `[]`] → destination stays unplannable; FE timeout copy; operator can retry prepare
- [Multi-worker in-flight lock] → `get_cache_backend()` is Redis when `REDIS_URL` set; empty URL is process-local (two workers may double-scrape once — idempotent OSM upserts)
- [Background task + process restart] → lock TTL must expire (e.g. 180s) so a dead worker does not pin `preparing` forever
- [Guest still 403 on another session’s trip] → unchanged; FE_guide already documents cookie host alignment (`localhost` vs `127.0.0.1`)
- [50 km still huge for a country centroid] → accepted until a later region change

## Migration Plan

1. Extract ingest module; keep CLI green
2. Service + router + limiter + tests (404, 200 ready, 202 kickoff, concurrent, 429, fail-open)
3. Update `docs/FE_guide.md` + `docs/context.md` Live endpoints
4. No Alembic
5. Rollback: remove route; CLI seed still works

## Open Questions

- None blocking. Enrich/index-after-prepare is a later change.
