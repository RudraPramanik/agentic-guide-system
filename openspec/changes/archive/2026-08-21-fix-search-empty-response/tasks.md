## 1. Settings and search bound

- [x] 1.1 Add `SEARCH_GEOCODE_TIMEOUT_SECONDS: float = 8.0` in `src/config.py`. Document it in `.env.example`.
- [x] 1.2 In `DestinationService.search`, wrap `geocode(query)` with `asyncio.wait_for` using that setting. On timeout, follow the same path as `geocode is None` (`DestinationNotFoundError`). Do not import geocode in the router. Do not use `os.environ.get()`.

## 2. Compose reload scope

- [x] 2.1 In `docker-compose.yml` api command, keep `--reload` and add `--reload-dir /app/src`. Do not watch all of `/app`.

## 3. Tests

- [x] 3.1 Add/extend a destinations test: when geocode hangs past the timeout, search raises `DestinationNotFoundError` (or the HTTP 404 `not_found` equivalent). DB ILIKE hit still returns without waiting on geocode.
- [x] 3.2 Run `python -m pytest` on the new/changed destinations tests `-v`.

## 4. Docs and proof

- [x] 4.1 Update `docs/issue_solve.md`: `ERR_EMPTY_RESPONSE` vs `ERR_CONNECTION_REFUSED`; geocode bound; `--reload-dir`.
- [x] 4.2 Recreate Compose `api` and prove `q=darjeeling` 200, `q=dhaka` HTTP JSON (200 or 404), not a dropped connection.
- [x] 4.3 Playwright: type `dhaka` on the running FE; search request must get an HTTP status, not `ERR_EMPTY_RESPONSE`.

## 5. Stop

- [x] 5.1 Do not change FE timeout, CORS, cookies, Overpass-on-search, or parent OpenSpec. Do not commit `.env`.
