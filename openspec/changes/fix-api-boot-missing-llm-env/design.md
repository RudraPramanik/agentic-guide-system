## Context

See `proposal.md` for why. Compose `api` runs `alembic upgrade head` then uvicorn. Both load `get_settings()`. `LLM_API_KEY: str` has no default. Alembic `env.py` already uses `get_settings().DATABASE_URL` (no `os.environ.get()`). Sibling FE calls `http://localhost:8000` directly (BFF deferred). Unused Next.js font preload is unrelated.

## Goals / Non-Goals

**Goals:**

- One wrapping point so Alembic and uvicorn share the same missing-env message.
- Docs map FE `:8000` `ERR_CONNECTION_REFUSED` to `wandr_api` not listening / missing `.env` keys.
- Host pytest proves the message without needing Docker.

**Non-Goals:**

- Optional `LLM_API_KEY` (catalog still must not boot without it — keeps generate misconfig loud).
- Next.js rewrites, CORS, cookie, or `NEXT_PUBLIC_API_URL` changes.
- New packages, endpoints, or env var names.
- Committing `.env`.

## Decisions

### 1. Wrap `get_settings()`, do not special-case Alembic

**Choice:** Catch Pydantic `ValidationError` in `get_settings()`, list `type=missing` locations, raise `RuntimeError` with those names plus “Compose `env_file` `.env` / `.env.example`”. Keep `@lru_cache` (failed calls are not cached).

**Why:** Alembic and uvicorn already share `get_settings()`. AGENT.md forbids `os.environ.get()`. A second Docker shell script would drift from host uvicorn.

**Alternative considered:** Make `LLM_API_KEY` default `""` so destinations search works without a key. Rejected — hides misconfig until generate; catalog boot without a key is out of scope.

**Alternative considered:** Read `DATABASE_URL` in `alembic/env.py` from os.environ. Rejected — AGENT.md env rule; uvicorn would still crash with the opaque traceback.

### 2. Docs in this repo only

**Choice:** `docs/context.md` local quick-ref, `docs/FE_guide.md` local verification (Compose now includes API; CONNECTION_REFUSED troubleshooting), `docs/app/system.md` run notes, `.env.example` comment that a commented/empty `LLM_API_KEY` leaves `:8000` unbound.

**Why:** Parent tripplanner vault is out of scope. Sibling FE does not own Compose boot.

### 3. Test via empty cwd, not the developer `.env`

**Choice:** `monkeypatch.chdir(tmp_path)` + `delenv("LLM_API_KEY")` + `get_settings.cache_clear()` so Settings cannot load the repo `.env`. Assert `RuntimeError` mentions `LLM_API_KEY` and `.env`. Always `cache_clear()` in `finally`.

**Why:** Host `.env` must keep a real key for Compose; the test must not depend on it.

## Risks / Trade-offs

- [Operators still put `LLM_*` in the Next `.env`] → Mitigation: FE_guide already says never put `LLM_*` in the frontend; boot message points at the API `.env`.
- [Message wrapping hides Pydantic URL] → Mitigation: `raise RuntimeError(...) from e` keeps the cause chain.
- [`.env` still missing the key after the code change] → Mitigation: operator restores `LLM_API_KEY` (and `LLM_API_BASE` if the model needs it); that file stays uncommitted.

## Migration Plan

No DB migration. Restart Compose `api` after `.env` has a non-empty `LLM_API_KEY`. Rollback: revert `get_settings()` wrapping; docs comments only.

## Open Questions

None.
