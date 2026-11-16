# Architecture violations allowlist (Slice 0.5)

Paths listed under **Allowlist** are known breaches. Architecture tests fail only on *new* paths for the same rule. Do not edit `src/` solely to clear an entry in this file.

## Allowlist

| Rule | Path | Note |
|------|------|------|
| G3 | src/core/observability/tracing.py | Writes Langfuse settings into `os.environ` for SDK fallbacks. Ticket: v83-s0-g3-tracing-environ (fix in a later change whose allowed paths include this module). |

## Deferred (§10 rules not enforced in this suite)

| Rule | Reason |
|------|--------|
| G8 | Owned by `tests/snapshots` (subslice 0.2 / `legacy-api-snapshots`). |
| G9 | Full requirements-diff check needs more than this row; no new package added here. |
| G10 | Alembic up/down belongs to migration CI, not `tests/architecture`. |
| G12 | Golden replay owned by eval harness (`run_evals`). |
| G13 | Flag-off differential snapshot work is later. |
| G14 | No `ValidationFinding` type or stable finding-code registry in the checkout yet; suite only guards if that type appears later. |
| G15 | No run-status service / `planner/runs/` yet — do not invent it. |
