## Context

See proposal.md — Why. This repo has no `.gitignore`. Git currently tracks `.env` (plus `__pycache__` / `*.pyc`). `.dockerignore` already excludes `.env` / `.env.*` with `!.env.example`. `get_settings()` and Compose `env_file: .env` stay unchanged — this is Git hygiene only.

Git ignore rules apply only to **untracked** paths. A file already in the index stays tracked until `git rm --cached`, even after `.gitignore` is added.

## Goals / Non-Goals

**Goals:**

- Root `.gitignore` so new local secrets and bytecode never enter the index.
- Remove `.env` and bytecode from the index without deleting working-tree files.
- Keep `.env.example` (and other templates) committed.
- Make the “already tracked vs ignore” distinction explicit so the next agent does not treat `.gitignore` as a history eraser.

**Non-Goals:**

- Rewriting git history or force-pushing.
- Changing settings loading, Compose, Dockerfiles, or `.dockerignore`.
- Sibling frontend ignore files.
- Publishing secret values in this change’s artifacts.

## Decisions

### D1 — Add a real root `.gitignore`; do not “fix” a missing file by editing Git config

Create `.gitignore` at the repo root with Python + secret patterns. Align env rules with `.dockerignore`:

```
.env
.env.*
!.env.example
```

Also ignore: `__pycache__/`, `*.py[cod]`, `.venv` / `venv`, pytest/mypy/ruff/coverage caches, `dist/` / `build/` / `*.egg-info/`, `.DS_Store` / `Thumbs.db`. Do **not** ignore `.cursor/`, `.cursorrules`, `.dockerignore`, or `.vscode/settings.json` (those are already committed project files).

**Alternatives:** Only ignore `.env` — rejected (bytecode is the same class of accident and already tracked). Copy `.dockerignore` wholesale — rejected (it excludes `docs/`, `tests/`, `openspec/`, which must stay in Git).

### D2 — Untrack with `git rm --cached`; never `git rm` without `--cached`

After `.gitignore` exists:

- `git rm --cached .env`
- `git rm -r --cached` on tracked `__pycache__` / `*.pyc`

Working tree `.env` stays for local Compose/pytest. `.env.example` stays tracked.

**Alternatives:** Leave `.env` tracked and hope ignore hides it — rejected (ignore cannot untrack). Delete `.env` from disk — rejected (breaks local dev).

### D3 — Stop the leak going forward; do not rewrite history in this change

Untracking removes `.env` from **future** trees. History and GitHub still contain old blobs. Operators must **rotate** keys that were in the committed file (`LLM_API_KEY`, `GEMINI_API_KEY`, OAuth client secret, `SECRET_KEY`, Qdrant key, etc.). History rewrite (filter-repo / BFG + force-push) is a separate, explicit request.

**Alternatives:** Rewrite history now — rejected (needs explicit operator consent; breaks clones). Make the repo private only — insufficient if the remote was ever public or cloned.

### D4 — Docs are a comment + context checkpoint, not a new spec

One comment on `.env.example`: copy to `.env` / `.env.production` locally; never commit those files. After validate, stamp `docs/context.md` (gitignore exists; `.env` untracked). No `openspec/specs/` delta (`skip_specs: true`).

**Alternatives:** New capability spec — rejected (no runtime behavior change).

## Risks / Trade-offs

- **[Secrets remain in git history / GitHub]** → Mitigation: rotate keys after the untrack commit is pushed; history rewrite only if the user later asks.
- **[Someone copies `.gitignore` but skips `rm --cached`]** → Mitigation: tasks.md makes untrack a required step; proof is `git check-ignore -v .env` **and** `git ls-files .env` empty.
- **[Negation un-ignores a secret]** → Mitigation: only `!.env.example`; never `!.env`.
- **[Large bytecode diff in the untrack commit]** → Acceptable; one-time index cleanup.

## Migration Plan

1. Add `.gitignore`.
2. `git rm --cached` secrets + bytecode (keep files on disk).
3. Comment `.env.example`; validate ignore + untrack.
4. Update `docs/context.md`.
5. After push: rotate exposed keys (operator, outside this repo change).

**Rollback:** Restore `.gitignore` / index from the previous commit. Do not re-add `.env` to Git.

## Open Questions

None — history rewrite is deferred as a non-goal, not an unknown.
