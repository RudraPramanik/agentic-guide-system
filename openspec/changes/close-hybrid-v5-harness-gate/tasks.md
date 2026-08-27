## 1. Preconditions

- [x] 1.1 Re-read `docs/context.md`, `AGENT.md`, and `docs/v2_blueprint.md` V5 cutover / V6 conditional sections; confirm V0–V6.1 code is present and this change is close-out only (no V6.2 implementation)
- [x] 1.2 Confirm local stack readiness: DB + Qdrant up; Darjeeling indexed on active `places_collection()` (non-zero `count_indexed`); `LLM_API_KEY` set for live generate; `SEARCH_SPARSE_ENABLED` as intended for the gate
- [x] 1.3 Narrow enrich: ensure every golden `must_include_places` name for Darjeeling has a non-null `summary` (at least Tiger Hill) — ops only, not full 244-place enrich; no ranking-code changes
- [x] 1.4 Reindex Darjeeling into active `places_collection()`; confirm must-include places are retrievable via `search_places` (e.g. Tiger Hill in top-k for exact-name query)

## 2. Live golden harness gate

- [x] 2.1 Run `python scripts/run_evals.py --destination darjeeling` **without** `--fixtures-only`; confirm run report under `evals/runs/` has case `mode` = live generate (not `fixture`)
- [x] 2.2 Require exit 0 vs `evals/baselines/darjeeling.json` for property assertions (`must_include_places`, `no_geo_fallback`, and related). If fails: triage reasons — do **not** change ranking code in this change; if baseline is fixture-era and live verdicts are acceptable after review, update with `--update-baseline` once and note why
- [x] 2.3 Mark `openspec/changes/hybrid-dense-sparse-place-search/tasks.md` item **6.2** complete

## 3. V6 go/no-go (evidence only)

- [x] 3.1 From the live harness outcome (and optional sample of `tool_trace` fusion diagnostics if available), record a one-line go/no-go: defer V6.2/V6.3 **or** “propose V6.2 later — retrieval-dominant misses”
- [x] 3.2 Do **not** implement embedding bump or cross-encoder in this change

## 4. OpenSpec hygiene and docs

- [x] 4.1 Archive `hybrid-dense-sparse-place-search` (sync delta specs to main as part of archive workflow)
- [x] 4.2 Archive or sync-complete `wire-langfuse-tracing-and-eval-harness` if implementation already matches unmarked tasks (no re-coding); leave unrelated in-progress changes alone
- [x] 4.3 Update `docs/context.md`: Last updated, Next step (FE companion / VPS / evidence-gated V6.2 per go/no-go — not “do V6.2 by default”), note V5 live harness gate closed

## 5. Proof

- [x] 5.1 Live harness exit 0 (or reviewed baseline update) with generate-mode cases documented
- [x] 5.2 No HTTP/SSE/FE contract changes; no new packages; pytest not required unless a triage fix was split out
