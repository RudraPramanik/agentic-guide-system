## Context

See proposal.md for motivation. Allowed paths are `tests/architecture/**` and the CI workflow only. `requirements.txt` is closed, so enforcement cannot add `import-linter`. Preflight found one G3 breach in `src/core/observability/tracing.py` (`os.environ[...] = settings.LANGFUSE_*`). Routers already import `get_db` / `AsyncSession` for FastAPI Depends wiring; they do not import repositories. Graph nodes import `execute_tool`, registry helpers, and schemas — not concrete tool modules such as `search_places`.

## Goals / Non-Goals

**Goals:**
- Ship AST/grep pytest that locks G1–G5, G7, G11, G14, and G16 for the current tree.
- Ticket existing breaches with a tight allowlist so new breaches fail.
- Make CI call architecture tests explicitly.

**Non-Goals:**
- Fixing `tracing.py` or any other `src/` file.
- Replacing G8/G10/G12/G13 (owned elsewhere) or inventing G15’s run service.
- Adding packages or editing `docs/context.md`.

## Decisions

### 1. AST/grep helpers, not import-linter
- **Choice:** Shared helpers under `tests/architecture/` walk `src/**/*.py` with the stdlib `ast` module and simple string/regex checks.
- **Why:** Allowed paths exclude `requirements.txt`. Stdlib is enough for the named rules.
- **Alternatives:** Add `import-linter` (rejected — new package). Shell `rg` only in CI (rejected — local `pytest tests/architecture` must match CI).

### 2. Allowlist file for known violations
- **Choice:** `tests/architecture/VIOLATIONS.md` lists `{rule_id, path, note}`. Tests load the paths for each rule and fail only on the set difference (found − allowlisted).
- **Why:** Row 0.5 verify allows “violations listed and ticketed”; the stop forbids fixing unrelated code.
- **Alternatives:** Leave tests red (rejected — CI would stay red and block unrelated PRs). Xfail whole rules (rejected — hides new breaches).

### 3. G5 and G4 interpretations
- **G5:** Fail on repository / `BaseRepository` imports from `*router.py`. Allow `get_db` and `AsyncSession` Depends imports already used everywhere.
- **G4:** Fail when `src/planner/graph/nodes/**` imports a concrete tool module under `src/planner/tools/` other than `registry`, `schemas`, and the `execute_tool` export surface. Allow registry/schema imports used by `agent.py` / `tool_executor.py`.
- **Why:** Matches AGENT.md intent without a production rewrite outside allowed paths.
- **Alternatives:** Ban all session imports in routers (would force `src/` churn). Ban all `planner.tools` imports from nodes (would false-fail current graph).

### 4. Scope of §10 in this subslice
- **In suite now:** G1, G2, G3, G4, G5, G7, G11, G14, G16; G6 limited to “no module-level ToolContext binding” AST check if cheap to express.
- **Deferred / owned elsewhere:** G8 (snapshots), G9 (optional CI comment only — full diff lint needs more than this row), G10 (migrations), G12/G13 (evals/differential), G15 (no run service yet).
- **Why:** Row 0.5 names import rules, no-`os.environ`, no litellm outside gateway, no I/O in `travel_engine`. Adjacent pure checks that fit the same folder are included; rules that invent modules or leave allowed paths are documented, not faked.

### 5. CI wiring
- **Choice:** In `.github/workflows/ci.yml` `test` job, add a step `Run architecture guardrails` with `pytest tests/architecture -v` before or after the existing `pytest tests/ -v`.
- **Why:** Row 0.5 lists “CI workflow”; an explicit step makes failures obvious even though the full suite would already collect `tests/architecture`.
- **Alternatives:** Rely only on `pytest tests/ -v` (weaker signal). Separate CI job (unnecessary duplication of Postgres setup).

### 6. `docs/context.md`
- **Choice:** Do not update it.
- **Why:** Same allowed-path conflict as 0.1–0.4. Architecture tests + VIOLATIONS.md are the completion record.

## Risks / Trade-offs

- [Allowlist rot] → Mitigation: each entry names rule id + path; tests assert allowlisted paths still exist and still match, so stale entries fail.
- [False positives on `import os` alone] → Mitigation: G3 matches `os.environ` / `os.getenv` use, not every `import os`.
- [G11 flag inventory drifts] → Mitigation: read flag names only from settings fields already documented in blueprint §7 / `src/config.py`; do not invent new flags.
- [G14 registry location wrong] → Mitigation: locate the existing finding-code enum/registry used by travel_engine validator before coding; halt if absent rather than inventing one.
- [OpenSpec wants context.md update] → Mitigation: report conflict; preserve row 0.5 allowed paths.

## Migration Plan

1. Land tests + VIOLATIONS.md + CI step on the feature branch.
2. Verify: `pytest tests/architecture -v` exits 0.
3. Rollback: delete `tests/architecture/**` and revert the CI step.

## Open Questions

None that block planning. G14 registry path is an apply-time locate-or-halt check, not a product decision.
