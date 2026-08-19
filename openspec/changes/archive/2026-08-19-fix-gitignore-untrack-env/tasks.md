## 1. Ignore file

- [x] 1.1 Add root `.gitignore` with `.env`, `.env.*`, and `!.env.example` (same env contract as `.dockerignore`). Also ignore `__pycache__/`, `*.py[cod]`, `.venv`/`venv`, pytest/mypy/ruff/coverage caches, `dist/`/`build/`/`*.egg-info/`, `.DS_Store`, `Thumbs.db`. Do not ignore `.cursor/`, `.cursorrules`, `.dockerignore`, `.vscode/`, `docs/`, `tests/`, or `openspec/`.
- [x] 1.2 Add a one-line comment at the top of `.env.example`: copy to local `.env` / `.env.production`; never commit those files. Do not change key names or example values.

## 2. Untrack leaked files

- [x] 2.1 `git rm --cached .env` so `.env` leaves the index. Confirm the working-tree file still exists (`Test-Path .env` / equivalent). Never `git rm .env` without `--cached`.
- [x] 2.2 `git rm -r --cached` tracked `__pycache__` directories and `*.pyc`. Leave source `.py` files tracked.
- [x] 2.3 Confirm `.env.example` is still tracked (`git ls-files .env.example`).

## 3. Proof, docs, stop

- [x] 3.1 Proof: `git check-ignore -v .env` matches `.gitignore`; `git ls-files .env` is empty; `git check-ignore -v .env.example` does **not** ignore the example; `git ls-files .env.example` still lists it.
- [x] 3.2 Update `docs/context.md`: Last updated date; note that root `.gitignore` exists and `.env` is untracked (history still has old blobs until a separate rewrite). Do not paste secret values.
- [x] 3.3 Stop — do not rewrite git history, force-push, edit `src/config.py`, Compose, Dockerfiles, or `.dockerignore`. After the untrack commit is on origin, the operator must rotate keys that were in the old committed `.env` (LLM, Gemini, OAuth, `SECRET_KEY`, Qdrant). Do not print those values in docs or chat.
