## 1. Boot error wrapping

- [x] 1.1 In `src/config.py`, wrap `get_settings()` so a Pydantic missing-field `ValidationError` becomes a `RuntimeError` that names the missing keys (including `LLM_API_KEY`) and points at Compose `env_file` `.env` / `.env.example`. Keep `@lru_cache`. Do not use `os.environ.get()`. Do not make `LLM_API_KEY` optional.
- [x] 1.2 Add a comment on `LLM_API_KEY` in `.env.example` that a commented or empty value makes Compose `api` exit before binding `:8000`.

## 2. Tests

- [x] 2.1 Add `tests/core/test_settings_boot.py`: chdir to a temp dir, `delenv("LLM_API_KEY")`, `get_settings.cache_clear()`, assert `RuntimeError` mentions `LLM_API_KEY` and `.env`. Always `cache_clear()` in `finally`.
- [x] 2.2 Run `python -m pytest tests/core/test_settings_boot.py -v` (no Postgres required).

## 3. Docs

- [x] 3.1 In `docs/context.md` local quick-ref, note that `wandr_api` Exited + host `:8000` connection refused usually means missing required `.env` (`LLM_API_KEY`); Postgres up is not enough. Point at `docker logs wandr_api`.
- [x] 3.2 In `docs/FE_guide.md` local verification, document `docker compose up --build` as the API start (not data-only compose + host uvicorn as the default), and that sibling FE `ERR_CONNECTION_REFUSED` to `:8000` / destinations search is API not listening — not a Next.js URL bug. Unused font preload is unrelated.
- [x] 3.3 In `docs/app/system.md` run notes, add the same CONNECTION_REFUSED → `wandr_api` / `LLM_API_KEY` mapping.

## 4. Local stack and stop

- [x] 4.1 Ensure the uncommitted local `.env` has a non-empty `LLM_API_KEY` (and `LLM_API_BASE` if the chosen model needs it). Do not commit `.env`.
- [x] 4.2 Restart Compose `api` and prove `GET /api/v1/health` and `GET /api/v1/destinations/search?q=darjeeling` on host `:8000`.
- [x] 4.3 Stop — do not change destinations/search, CORS, cookies, sibling frontend code, or parent tripplanner OpenSpec.
