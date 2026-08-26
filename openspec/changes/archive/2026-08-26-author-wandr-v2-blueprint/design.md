## Context

See `proposal.md` — Why. Post-P7 work is scattered (`docs/next_version.md`, `docs/ci_cd_plan.md`, OpenSpec hybrid + Langfuse changes). This change authors `docs/v2_blueprint.md` in the **same step-by-step shape** as `docs/blueprint_final.md` (legend: package / LLD / failure / proof) so agents can execute V0–V6 without re-deriving order or fallbacks.

Constraints carried in:
- v6.1 remains SSOT for shipped P0–P7 (`docs/blueprint_final.md`).
- Architecture rules in `AGENT.md` unchanged.
- Prefer **max fail-soft**: every new external/optional path degrades to today's working behavior.
- Code implementation of hybrid/Langfuse stays in sibling OpenSpec changes; this file is the human build bible.

## Goals / Non-Goals

**Goals:**
- One phased blueprint (V0–V6) with per-step ✅ proofs and 🚨 failure boundaries.
- Explicit degradation ladders (sparse → dense → geo → `[]`; tracer → NoOp; usage missing → empty).
- Kill-switches and dual-collection cutover so ranking can change without API/FE breaks.
- Close review gaps: expand `_canonical_text` for BM25 (name ± category) before RRF cutover; note `flush_tracer()` already in lifespan; three `query_points` tests; single collection accessor.

**Non-Goals:**
- Implementing any V* step in this change.
- Rewriting v6.1 or inventing new HTTP APIs.
- Choosing CD Phase B now.

## Decisions

### D1 — `docs/v2_blueprint.md` is the v7 build SSOT; `next_version.md` stays a notes companion
Agents read v2_blueprint for step order. `next_version.md` retains detailed package-decision tables; v2_blueprint links to it rather than duplicating essays.

**Alternative:** Expand only `next_version.md` — rejected; it lacks P0–P7-style step granularity and legend.

### D2 — Phase IDs V0–V6 (not P8+)
Avoid colliding with Progress-table P0–P7 in `docs/context.md`. V-phases are post-P7 upgrades.

### D3 — Sequencing locked (fail-soft gate before ranking change)
```
V0 CI → V1 query_points → V2 observability → V3 golden harness
  → V4 canonical-text for sparse → V5 hybrid RRF → V6 evidence polish (optional)
```
Harness before RRF so cutover is proven. Canonical-text expansion before RRF so BM25 can see place names (review finding).

### D4 — Max fallback is a first-class principle in v2
Every V-step documents the ladder back to v6.1 behavior. Default config keeps generate working with empty Langfuse keys, sparse kill-switch, and PostGIS geo fallback unchanged.

### D5 — Sibling OpenSpec ownership
| Work | OpenSpec change |
|------|-----------------|
| Token/Langfuse/harness code | `wire-langfuse-tracing-and-eval-harness` |
| Hybrid RRF code | `hybrid-dense-sparse-place-search` (fill tasks from v2 blueprint V1/V4/V5) |
| Minimal CI | follow `docs/ci_cd_plan.md` Phase A (may be a thin follow-up change) |
| This docs bible | `author-wandr-v2-blueprint` |

### D6 — No new packages in default path
Pure-Python BM25; hand-rolled eval runner; langfuse already pinned. Revisit triggers stay in `next_version.md`.

## Risks / Trade-offs

- [Blueprint drifts from code again] → Cite exact modules (`places_index.py`, `TravelState`, etc.); re-verify before V5 apply.
- [Duplicate SSOT confusion vs next_version.md] → v2_blueprint header states primacy for *build steps*; next_version for *package decisions / why tables*.
- [Empty hybrid OpenSpec tasks] → V5 section is detailed enough to fill that change's tasks.md later; not done in this change.
- [Writing blueprint without implementing] → Intentional: docs-only change; apply = author file + pointers.

## Migration Plan

1. Write `docs/v2_blueprint.md` from this design's phase outline (full step text).
2. Add pointer at top of `docs/next_version.md` → v2_blueprint as build SSOT.
3. Optionally bump `docs/context.md` Next-step line to mention v2_blueprint (no fake Progress rows).
4. Rollback: git revert of those docs only.

## Open Questions

None for this docs change. Implementation-time questions (exact `LLMUsage` return shape) belong in `wire-langfuse-tracing-and-eval-harness` design, already noted there.
