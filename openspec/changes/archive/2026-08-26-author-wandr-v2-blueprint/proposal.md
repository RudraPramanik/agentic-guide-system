## Why

Post-P7 work is split across `docs/next_version.md` (v7.0/v7.1 notes), `docs/ci_cd_plan.md`, and two OpenSpec changes (`wire-langfuse-tracing-and-eval-harness`, empty `hybrid-dense-sparse-place-search`). Agents need a **single step-by-step build bible** in the same shape as `docs/blueprint_final.md` (v6.1) — ordered phases, per-step proofs, resilience contracts, and fail-soft ladders — before coding starts. Without it, sequencing (CI → observability harness → RRF cutover) and fallback rules get rediscovered each session.

## What Changes

- **Docs only** — authors `docs/v2_blueprint.md` as the post-P7 / v7 build SSOT (does **not** supersede `docs/blueprint_final.md` for P0–P7).
- Fold corrected sequencing and review findings into one phased blueprint: minimal CI → `query_points` → observability → golden harness → expand sparse/dense canonical text (name ± category) → hybrid RRF `places_v2` → evidence-gated polish.
- Emphasize **max fail-soft**: every new path has a named degradation that preserves generate / trips / SSE / auth contracts; kill-switches and dual-collection cutover documented.
- Point implementers at existing OpenSpec changes for code work; this change does not re-spec hybrid or Langfuse behavior.
- Optionally add a one-line pointer from `docs/next_version.md` / `docs/context.md` to `docs/v2_blueprint.md` as the build SSOT (no Progress-table phase inventing).

## Capabilities

### New Capabilities

(none — docs-only change)

### Modified Capabilities

(none — no spec-level behavior changes; `.openspec.yaml` sets `skip_specs: true`)

## Impact

- **Files changed:** `docs/v2_blueprint.md` (primary); optional pointer lines in `docs/next_version.md` and/or `docs/context.md`.
- **No impact on:** product code, tests, dependencies, DB schema, API surface, planner tool contracts.
- **Downstream:** implementation follows V0–V6 steps in `docs/v2_blueprint.md`; use `/opsx-apply` on `wire-langfuse-tracing-and-eval-harness` and a filled hybrid change for code — not this change.

## Non-goals

- No implementation of CI, hybrid search, Langfuse, or eval harness in this change.
- No edits to `docs/blueprint_final.md` (v6.1 remains Planner/backend SSOT for shipped P0–P7).
- No full CD (Phase B) — deferred per `docs/ci_cd_plan.md`.
- No cross-encoder, fastembed, or new packages in the blueprint as default path.
- No API/frontend contract changes in any v7 stage described by the blueprint.
