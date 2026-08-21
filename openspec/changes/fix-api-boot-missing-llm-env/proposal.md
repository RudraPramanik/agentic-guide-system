## Why

Sibling frontend destination search (`GET /api/v1/destinations/search`) fails with browser `net::ERR_CONNECTION_REFUSED` on `:8000` while Compose Postgres/Qdrant/Redis look healthy. The API container never binds the port: `alembic upgrade head` calls `get_settings()`, `LLM_API_KEY` is required, and a local `.env` with that key commented/empty makes `wandr_api` exit 1. Operators (and the frontend) see a network error instead of a missing-env boot failure. The unused Next.js font preload warning is unrelated.

## What Changes

- `get_settings()` MUST turn a Pydantic missing-field `ValidationError` into an operator-readable boot error that names the missing keys (at least `LLM_API_KEY`) and points at Compose `env_file` `.env` / `.env.example`. Alembic and uvicorn both go through this path — no `os.environ.get()` in app code.
- Document the FE symptom: `ERR_CONNECTION_REFUSED` to `localhost:8000` (including destinations search) means `wandr_api` is not listening. Postgres up is not enough. Check `docker compose ps` / `docker logs wandr_api`. `LLM_API_KEY` is required to boot even for catalog routes that do not call the LLM.
- pytest covers the boot message when `LLM_API_KEY` is absent.
- **Non-goals:** Do not change destinations/search, CORS, cookie policy, Next.js, `NEXT_PUBLIC_API_URL`, or make `LLM_API_KEY` optional. Do not add endpoints, packages, or env var names. Do not commit `.env`. Font preload unused is out of scope.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `local-docker-dev-stack`: When required Settings fields are missing (including `LLM_API_KEY`), the API process MUST fail fast with an operator-readable message naming those fields and the Compose `.env` `env_file`. Docs MUST map frontend `:8000` `ERR_CONNECTION_REFUSED` to this boot failure, not to a frontend URL bug.

## Impact

- `src/config.py` (`get_settings()`)
- `tests/core/` boot/settings test
- `docs/FE_guide.md`, `docs/context.md`, `docs/app/system.md` (local boot / CONNECTION_REFUSED)
- `.env.example` comment that `LLM_API_KEY` must be uncommented and non-empty for Compose `api` to bind `:8000`
- AGENT.md: env still only via `get_settings()`; no new packages; no invented endpoints
- Local uncommitted `.env` must actually contain `LLM_API_KEY` (and `LLM_API_BASE` when the chosen model needs it) for the stack to listen — that is operator config, not a committed file
- Sibling frontend unchanged
