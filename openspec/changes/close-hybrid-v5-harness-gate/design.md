## Context

See proposal.md — Why. V4–V5 hybrid code and V6.1 fusion diagnostics are already in tree; `docs/context.md` marks them done. The remaining gap is operational: `hybrid-dense-sparse-place-search` task 6.2 and the blueprint’s “harness before / after ranking change” gate. Current `evals/baselines/darjeeling.json` cases show `mode: fixture`, so live retrieval after RRF is not yet the frozen gate artifact.

Constraints: no API/FE delta; no new packages; fail-soft search unchanged; FakeRoutingProvider for harness (existing runner); all env via `get_settings()`.

## Goals / Non-Goals

**Goals:**
- Prove hybrid cutover with a live golden harness pass (or an explicit, reviewed baseline refresh).
- Produce a short V6 go/no-go from harness outcomes + optional fusion diagnostics (evidence only).
- Close OpenSpec hygiene: mark hybrid 6.2 done; archive completed changes; update `docs/context.md` Next step.

**Non-Goals:**
- Implementing V6.2 embedding bump or V6.3 cross-encoder.
- Changing RRF / sparse / dense ranking code unless a live regression forces a **separate** fix change.
- Expanding the golden case set or adding LLM-as-judge.
- FE or VPS work (follow-on after this close-out).

## Decisions

### 1. Dedicated close-out change vs only ticking hybrid task 6.2
**Choice:** New change `close-hybrid-v5-harness-gate` that finishes 6.2, clarifies live-vs-fixture gate in specs, then archives.
**Why:** Specs currently say “harness passes” without distinguishing fixtures-only; baselines are fixture-mode; archival + context Next-step rewrite need an explicit scope.
**Alternatives:** Apply remaining checkbox inside hybrid change only — weaker documentation of the live-gate rule and no clean place for V6 go/no-go.

### 2. Live harness command
**Choice:** `python scripts/run_evals.py --destination darjeeling` with stack up, Darjeeling indexed on active collection, `LLM_API_KEY` set, **without** `--fixtures-only`.
**Why:** Runner already switches to `PlannerService.generate` + ensures Qdrant/embeddings when key present (`mode: generate`).
**Alternatives:** HTTP SSE smoke only — weaker property coverage than golden assertions.

### 3. Baseline mismatch handling
**Choice:** If live run fails assertions or differs only because baseline was fixture-era: review per-case reasons; if product behavior is acceptable, `--update-baseline` once and document in context/notes. If retrieval regressions (e.g. geo-fallback spikes, must_include misses), **stop** — open a fix change; do not “tune” RRF in this change.
**Why:** Principle 15 — harness gates ranking; silent baseline overwrite hides regressions.
**Alternatives:** Always overwrite baseline — rejected.

### 4. V6 go/no-go criteria (evidence, not implementation)
**Choice:** After live harness:
- **Defer V6.2/V6.3** if pass_rate healthy, `no_geo_fallback` / `must_include_places` hold, and fusion diagnostics (when sampled) do not show systematic sparse/dense miss patterns dominating failures.
- **Propose V6.2 later** only if retrieval-dominant misses persist (wrong POIs / geo-fallback) with diagnostics implicating embedding vocabulary — not narrative/LLM flakiness.
**Why:** Matches `docs/v2_blueprint.md` V6 conditional wording.

### 5. Archive scope
**Choice:** After 6.2 + docs: archive `hybrid-dense-sparse-place-search`. Also archive or sync-mark `wire-langfuse-tracing-and-eval-harness` if implementation already matches unmarked tasks (no re-implementation). Leave unrelated in-progress changes (`allow-loopback-cors-origins`, `wandr-backend-roadmap`, `revise-next-version-build-plan`) alone unless user asks.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Live harness flaky (LLM nondeterminism) | Property assertions only (never exact narrative); FakeRoutingProvider; re-run once; investigate persistent fails |
| Empty / partial V2 index → false geo-fallback fails | Confirm `count_indexed` / readiness before gate; reindex Darjeeling if needed |
| Baseline update hides regression | Require human review of FAIL reasons before `--update-baseline` |
| Scope creep into V6.2 | Explicit non-goal; go/no-go note only |
| Long runtime / LLM cost | Darjeeling golden set only; one destination |

## Migration Plan

1. Ensure compose/API deps healthy; Darjeeling places indexed into active `places_collection()`.
2. Run live harness; save `evals/runs/<ts>-<sha>.json`.
3. Exit 0 → mark hybrid 6.2; optional baseline refresh only if modes/verdicts warrant.
4. Exit non-0 → triage; no ranking code changes in this change unless user opens a fix.
5. Write V6 go/no-go one-liner into `docs/context.md` Next step.
6. Archive OpenSpec changes; sync delta specs to main on archive.

**Rollback:** N/A for docs/ops. Product rollback remains env: `SEARCH_SPARSE_ENABLED=false` and/or `QDRANT_PLACES_COLLECTION=places`.

## Open Questions

- None that block tasks: if live harness is unavailable (no LLM key / no stack), apply stops at a blocked proof task rather than inventing a fixtures-only “pass.”

## Apply note (2026-08-26)

Live harness first run (`mode: generate`) failed partly because golden `must_include` **Tiger Hill** had `summary IS NULL` and was excluded from `index_places` (34/278 indexed). Decision: **narrow enrich** of must-include POIs + reindex + re-run — not full catalog enrich, not V6.2 ranking changes.
