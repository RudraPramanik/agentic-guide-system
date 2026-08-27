## Why

V0–V6.1 code is landed (`docs/v2_blueprint.md`; `docs/context.md`), but the hybrid change still has an open cutover gate: task **6.2** — run `scripts/run_evals.py` against the **real** stack (not `--fixtures-only`) and exit 0 vs baseline. Existing Darjeeling baselines record `mode: fixture`, so the V5 “harness-gated cutover” claim is not formally closed. Closing that gate now proves ranking stayed healthy after hybrid RRF, produces evidence for whether V6.2/V6.3 are needed, and lets us archive stale OpenSpec work — without shipping new retrieval features.

## What Changes

- Run (or re-run) the golden harness on the live stack against the active places collection (`places_v2` / accessor) with sparse on; require exit 0 vs `evals/baselines/darjeeling.json` for `must_include_places` / `no_geo_fallback` (and related assertions).
- If live run fails solely because the baseline was frozen from fixtures, update baseline **explicitly** (`--update-baseline`) only after reviewing live verdicts — never silently.
- Record a short V6 go/no-go note from harness + optional `tool_trace` fusion diagnostics (retrieval-dominant misses? yes → consider V6.2 later; no → leave V6.2/V6.3 deferred).
- Mark `hybrid-dense-sparse-place-search` task 6.2 complete; archive that change (and sync/archive `wire-langfuse-tracing-and-eval-harness` if code already matches unmarked tasks).
- Update `docs/context.md` Next step away from “do V6.2 next” unless evidence demands it (prefer FE companion or VPS after this close-out).

**Non-goals:** V6.2 embedding model bump; V6.3 cross-encoder; new packages; HTTP/SSE/FE contract changes; mutating retrieval ranking logic; full CD Phase B; inventing new golden cases unless a live case is malformed.

No **BREAKING** API changes.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `hybrid-dense-sparse-search`: Clarify that the dual-collection cutover checklist is closed only after a **live** (non-fixtures-only) golden harness pass against the active V2 collection; fixtures-only MUST NOT alone close cutover.
- `eval-golden-harness`: Clarify that cutover / ranking-regression gates MUST use live pipeline runs when the stack can generate; reports MUST keep distinguishing `fixture` vs live mode so operators do not confuse the two.

## Impact

- **Code:** None expected for the happy path (ops + docs + OpenSpec archive). Fix only if live harness exposes a real regression (then stop and open a separate fix change — do not silently “polish” ranking here).
- **APIs / FE:** Unchanged (principle 17).
- **Deps:** None.
- **Ops:** Needs local/dev stack with Qdrant indexed for Darjeeling, DB, and LLM key for live generate path; may take several minutes.
- **Docs / OpenSpec:** `docs/context.md`; complete/archive `hybrid-dense-sparse-place-search`; optionally archive `wire-langfuse-tracing-and-eval-harness`.
- **AGENT.md:** Fail-soft preserved; no new packages; do not invent endpoints.
- **Blueprint:** Closes V5 cutover proof in `docs/v2_blueprint.md`; does **not** start V6.2/V6.3.
