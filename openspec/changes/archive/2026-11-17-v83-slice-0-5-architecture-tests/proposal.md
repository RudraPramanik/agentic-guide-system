## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9, subslice **0.5**, and §10) asks for machine-enforced architecture guardrails under `tests/architecture/` so later slices cannot quietly break AGENT.md invariants. There is no `docs/steps/step*.md` for this work; the task id is blueprint row 0.5. Subslices 0.1–0.4 are archived. Guardrails still exist only as prose.

## What Changes

- Add pytest architecture tests under `tests/architecture/**` that enforce the Slice 0 import and purity rules from §10: LLM SDK imports only in the gateway (G1), no I/O imports inside `travel_engine` (G2), no `os.environ` / `os.getenv` outside `src/config.py` (G3), graph nodes do not import tool implementations (G4), and routers do not import repositories (G5).
- Add adjacent §10 checks that stay inside the allowed paths and need no new package: graph state has no `AsyncSession` / `RoutingProvider` fields (G7), feature flags default off/legacy (G11), `ValidationFinding.code` values stay in the stable registry (G14), and planner service / `travel_engine` do not import a lodging client or `src/geo/media/` (G16).
- Wire an explicit architecture pytest step into `.github/workflows/ci.yml` so every PR runs `pytest tests/architecture -v` (in addition to the existing full suite).
- If the current tree already violates a rule, list the paths in `tests/architecture/VIOLATIONS.md` with a ticketed allowlist. Tests stay green by failing only on *new* violations. Do not edit `src/` to clear them.
- No production behavior changes. No **BREAKING** changes.

Preflight already found one G3 hit: `src/core/observability/tracing.py` writes Langfuse keys into `os.environ`. That is reported and allowlisted. It is not fixed in this subslice.

## Capabilities

### New Capabilities

- `s0-architecture-guardrails`: pytest + CI enforce the Slice 0 architecture rules; known violations are listed and allowlisted; no silent new breaches.

### Modified Capabilities

- `github-actions-ci`: the Phase A `test` job MUST also run `pytest tests/architecture -v` (or an equivalent explicit architecture step) on every push and pull request to `main`.

## Impact

- **Work surface:** `tests/architecture/**` and the CI workflow only.
- **Files written:** architecture tests, a shared AST/grep helper if needed, `tests/architecture/VIOLATIONS.md` (allowlist + ticket notes), and a small edit to `.github/workflows/ci.yml`.
- **No new package:** enforcement is AST/grep pytest. `import-linter` is out because `requirements.txt` is outside the allowed paths.
- **No impact on:** application code, migrations, settings, HTTP paths, DTO shapes, SSE event names, Docker Compose, the eval runner, or `docs/context.md`.
- **Downstream:** Slice 0 exit gate and later slices treat architecture tests as merge blockers. Slice 1 may start after this subslice is archived.

## Non-goals

- No edits under `src/` to clear existing violations (blueprint stop: report; do not "fix" unrelated code).
- No `import-linter` dependency and no `requirements.txt` change.
- No re-implementation of G8 (owned by `legacy-api-snapshots` / 0.2), G10 (Alembic up/down — outside this row unless already in CI), G12 (golden replay — eval harness), or G13 (flag-off differential — later).
- No G15 run-status transition test until a run service exists; the suite records that deferral instead of inventing `planner/runs/`.
- No G6 concurrency harness beyond a static "no module-global ToolContext" AST check if the full two-generate isolation test needs production hooks outside allowed paths.
- No update to `docs/context.md`. Row 0.5's allowed paths forbid it, the same way 0.1–0.4 left that file alone.
- No Slice 1 run tracking and no product flag flips.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Stay inside `tests/architecture/**` and the CI workflow. Any other write is a stop.
- Prefer AST/grep tests over new tooling. A new package would need `requirements.txt`, which this subslice cannot edit.
- Treat the row 0.5 halt seriously: when a violation already exists, ticket it under `tests/architecture/VIOLATIONS.md` and keep the allowlist tight. Do not rewrite production modules so the test is easier to pass.
- Interpret G5 as: `*router.py` must not import `*repository*` / `BaseRepository`. FastAPI `Depends(get_db)` / `AsyncSession` wiring already used by every router is allowed; rewriting that pattern would touch `src/` and is out of scope.
- Interpret G4 as: `src/planner/graph/nodes/**` must not import concrete tool modules under `src/planner/tools/` that implement side effects. Imports of `execute_tool`, the registry, and schemas remain allowed.
- Not update `docs/context.md`. The OpenSpec repo rule asks for that update when a build step completes; row 0.5's allowed paths override it. The architecture suite and VIOLATIONS file are the record.
