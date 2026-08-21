## Why

Compose `wandr_api` still dies before binding `:8000` when `LLM_API_KEY` is missing or commented in the gitignored `.env`. Sibling FE then shows `ERR_CONNECTION_REFUSED` / empty destination search even though Postgres, Qdrant, and Redis are healthy. Change `fix-api-boot-missing-llm-env` only made that crash readable and relied on restoring a local secret — that is not durable across fresh clones, reset `.env`, or accidental comments. Catalog routes do not call the LLM; boot must not depend on an LLM secret.

## What Changes

- **BREAKING (boot contract):** `LLM_API_KEY` becomes optional at process start (default empty). Alembic + uvicorn MUST bind `:8000` when other required settings (`SECRET_KEY`, `DATABASE_URL`, `NOMINATIM_USER_AGENT`, …) are present, even if `LLM_API_KEY` is unset, commented, or empty.
- LLM gateway (`src/core/llm/client.py`) MUST refuse empty/whitespace keys with `WandrLLMError` before LiteLLM — generate/enrich stay loud when misconfigured; catalog/health/places stay up.
- Keep `get_settings()` operator-readable wrapping for *other* missing required fields; stop claiming `LLM_API_KEY` is required for catalog boot.
- Update `.env.example`, `docs/context.md`, `docs/FE_guide.md`, `docs/app/system.md`, and track the incident + permanent fix in `docs/issue_solve.md`.
- pytest: boot succeeds without `LLM_API_KEY`; empty-key LLM call fails clearly; replace the old “missing key blocks boot” expectation.

### Non-goals

- No new endpoints, env var names, or packages.
- No destinations/search, CORS, cookie, or sibling Next.js changes.
- Do not commit `.env` or real API keys.
- Do not weaken generate architecture (LLM still only via `core/llm/client.py`; planner still fail-soft on `WandrLLMError` where already designed).
- Parent `tripplanner/` OpenSpec out of scope.

## Capabilities

### New Capabilities

- _(none)_

### Modified Capabilities

- `local-docker-dev-stack`: Catalog/API boot MUST succeed without `LLM_API_KEY`. Missing LLM key MUST fail at the LLM gateway (generate/enrich), not at Alembic/uvicorn bind. Prior requirement that `LLM_API_KEY` remain required even for catalog routes is superseded.

## Impact

- `src/config.py` — `LLM_API_KEY` default `""`; boot error copy
- `src/core/llm/client.py` — empty-key guard
- `tests/core/test_settings_boot.py` (+ LLM empty-key test as needed)
- Docs: `docs/issue_solve.md`, `docs/context.md`, `docs/FE_guide.md`, `docs/app/system.md`, `.env.example`
- AGENT.md: env still only via `get_settings()`; LLM still only via gateway
- Supersedes the operational assumption of `fix-api-boot-missing-llm-env` (clearer missing-env messages for other fields remain valuable)
- Sibling frontend unchanged; `NEXT_PUBLIC_API_URL=http://localhost:8000` stays correct
