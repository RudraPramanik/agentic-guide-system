## Why

Secrets are in git because this repo has **no `.gitignore`**, and `.env` was committed anyway. Ignore rules never applied; `.gitignore` cannot hide a file that is already tracked. `.env` has been in history since early scaffold commits and is on `origin` (`agentic-guide-system`). `.dockerignore` already excludes `.env` — Docker is not the leak; Git is.

## What Changes

- Add a root `.gitignore` that ignores local env files, Python bytecode, venvs, caches, and OS junk, while **keeping** `.env.example` (and other committed templates) tracked.
- Stop tracking `.env` and `__pycache__` / `*.pyc` with `git rm --cached` so local files stay on disk but leave the index.
- Add a one-line operator note in `.env.example` (and a short `docs/context.md` checkpoint) that local `.env` / `.env.production` must never be committed.
- After the ignore+untrack commit is pushed, **rotate** every secret that lived in the committed `.env` (LLM, Gemini, OAuth, JWT `SECRET_KEY`, Qdrant, etc.). History still contains the old file until a separate history-rewrite is explicitly requested.
- **Non-goals:** No git history rewrite (`filter-repo` / BFG / force-push). No `src/config.py` or `get_settings()` changes. No `.env.example` key/value contract changes beyond the “do not commit” note. No sibling frontend repo. No new packages, endpoints, or env var names.

## Capabilities

### New Capabilities

- _(none — `skip_specs: true`; tooling/hygiene only)_

### Modified Capabilities

- _(none)_

## Impact

- New: `.gitignore` at repo root
- Git index: untrack `.env` and bytecode; keep `.env.example`
- Docs: `.env.example` comment; `docs/context.md` after validate
- No runtime, API, Docker Compose, or settings-schema change
- Operators: rotate keys already published in git history (GitHub remote)
