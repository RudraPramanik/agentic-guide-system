## Context

See `proposal.md`. Sibling FE `fetch` uses a 20s `AbortSignal`. `DestinationService.search` is DB ILIKE then `geocode()` (httpx read 10s, 3 retries, 1 req/s throttle). Compose runs `uvicorn --reload` with cwd `/app`. Chrome `ERR_EMPTY_RESPONSE` is a dropped TCP connection, not 404 JSON. Geo stays in `src/geo/`. Search still MUST NOT call Overpass.

## Goals / Non-Goals

**Goals:**

- Search always ends with HTTP 200 or 404 inside the FE abort window.
- Reload still works for `src/` edits without watching all of `/app`.
- Document empty-response vs connection-refused.

**Non-Goals:**

- Changing FE timeout, debounce, or Next rewrites.
- Returning `200 []` for unknown queries (spec stays 404 `not_found`).
- Removing `--reload` or changing lifespan MiniLM.
- New packages.

## Decisions

### 1. Bound geocode in the service, not the geocoder

**Choice:** `asyncio.wait_for(geocode(query), timeout=settings.SEARCH_GEOCODE_TIMEOUT_SECONDS)` in `DestinationService.search`. Timeout → same path as `geocode is None` (`DestinationNotFoundError`).

**Why:** Other geocode callers (seed CLI) can keep the existing retry budget. Search is the HTTP path that races the FE abort.

**Alternative considered:** Lower httpx retries globally. Rejected — seed/ingest need the current resilience contract.

### 2. `--reload-dir /app/src`

**Choice:** Add `--reload-dir /app/src` to the Compose uvicorn command; keep `--reload`.

**Why:** Default WatchFiles on cwd `/app` plus Windows bind mounts restart the worker mid-request (empty TCP). Spec already says reload is for application source.

**Alternative considered:** Disable reload in Docker. Rejected — local-docker-dev-stack requires reload without rebuild.

### 3. Settings field, not a literal 8

**Choice:** `SEARCH_GEOCODE_TIMEOUT_SECONDS: float = 8.0` in `src/config.py` and `.env.example`. Must stay under FE 20s with margin.

**Why:** AGENT.md forbids hardcoded timeouts outside settings.

## Risks / Trade-offs

- [Slow Nominatim on first miss returns 404 instead of waiting] → Mitigation: retry the same query after Nominatim is warm; DB hit on the next search. Catalog UX prefers a fast 404 over a hung socket.
- [8s still too long if the client aborts at debounce] → Mitigation: abort still cancels; next keystroke is a new request. Bound stops the *server* from overlapping retries after the client is gone.
- [Operators rely on reload of `scripts/`] → Mitigation: run scripts via `docker compose exec`; they are not the ASGI app.

## Migration Plan

No DB migration. Recreate Compose `api`. Rollback: remove `wait_for` and `--reload-dir`.

## Open Questions

None.
