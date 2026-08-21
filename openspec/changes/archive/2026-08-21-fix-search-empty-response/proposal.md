## Why

Sibling FE `GET /api/v1/destinations/search` sometimes fails in Chrome with `net::ERR_EMPTY_RESPONSE` (e.g. `q=dhaka`, `q=ba`, `q=barlin`) even when Compose `wandr_api` is healthy. That is not `ERR_CONNECTION_REFUSED` (nothing listening) and not a Next.js URL bug. Cached DB hits return JSON quickly; Nominatim cache-aside on a miss can run past the FE 20s abort (httpx read 10s × 3 retries + backoff). Client abort plus Compose `uvicorn --reload` watching all of `/app` on a Windows bind-mount can reset the TCP connection with no HTTP status.

## What Changes

- Cap destination-search geocode with `asyncio.wait_for` using a Settings timeout (`SEARCH_GEOCODE_TIMEOUT_SECONDS`, default 8s) so search always finishes with HTTP (`200` list or `404 not_found`) inside the FE abort window. Do not call Nominatim from the router. Still `get_settings()` only.
- On geocode timeout, treat as miss (`DestinationNotFoundError` / 404) — do not leave the connection open until WatchFiles or the client abort drops it.
- Scope Compose uvicorn `--reload` to `/app/src` only (`--reload-dir /app/src`) so bind-mount noise under `/app` does not restart the worker mid-request. Keep `--reload` (local-docker-dev-stack source-reload contract).
- Document `ERR_EMPTY_RESPONSE` vs `ERR_CONNECTION_REFUSED` in `docs/issue_solve.md`.
- **Non-goals:** No FE timeout/retry/CORS/cookie changes. No new endpoints. Do not scrape Overpass on search. Do not commit `.env`. Do not disable reload entirely. Nonsense queries stay 404 `not_found`.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `destinations-http`: Search MUST bound Nominatim wait and always emit an HTTP envelope (200 or 404) instead of dropping the connection.
- `local-docker-dev-stack`: Local Compose uvicorn `--reload` MUST watch application source only (`/app/src`), not the entire `/app` tree.

## Impact

- `src/config.py` — `SEARCH_GEOCODE_TIMEOUT_SECONDS`
- `src/destinations/service.py` — `wait_for` around `geocode`
- `docker-compose.yml` — `--reload-dir /app/src`
- `tests/destinations/` — timeout → 404, DB hit still 200
- `docs/issue_solve.md`, `.env.example`
- AGENT.md: env via `get_settings()`; geo still only via `src/geo/`; no new packages
