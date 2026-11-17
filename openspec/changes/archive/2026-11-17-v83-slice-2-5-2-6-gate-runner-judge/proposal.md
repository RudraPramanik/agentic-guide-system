## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9 rows **2.5** and **2.6**, plus §11.1, §11.3–§11.4, §11.7–§11.8) is the remaining Slice 2 work after archived `v83-slice-2-2-2-4-replay-metrics-properties`. There is no `docs/steps/step*.md` for these rows. Today `scripts/run_evals.py` diffs case pass→fail only, still scores quarantined cases into the gate, has no tolerance bands, and CI has no eval job. There is no `src/evaluation/judge/` and no human-review sheet. Without a named regression gate and an offline judge scaffold, later slices cannot prove non-regression or start judge calibration.

The user asked for rows 2.5 and 2.6 in one change, applied in that order. The blueprint's "one PR per subslice" rule is overridden for this batch only. Each row's stop condition still applies inside the change. 2.6 uses the gateway and flag contracts from this change and does not redefine the 2.5 gate.

## What Changes

- Harden the gate runner: exclude `quarantined` cases from gate pass rate and regression; keep them in the report under a separate bucket; print named regression codes; exit non-zero on regression.
- Add tolerance-band comparison for metrics that already have a measured baseline variance. Metrics whose S0 variance is still unmeasured are reported and MUST NOT hard-fail the gate (blueprint §11.4).
- Keep `--update-baseline` explicit and reviewed: it writes the new baseline only when that flag is set; a normal run never mutates baselines.
- Add a seeded regression unit path that forces a known pass→fail and asserts a named non-zero exit (row 2.5 required test).
- Add CI: PR/main job runs the golden suite in `--replay`; a scheduled nightly job runs live (or records a blocking ticket on live regression). Existing pytest/docker jobs stay.
- Add offline judge scaffold under `src/evaluation/judge/**`: LiteLLM only via the existing gateway; versioned prompt + rubric; sampled; never imported from the request path. Default `EVALUATION_JUDGE_ENABLED=false` and `EVALUATION_JUDGE_TIMEOUT_SECONDS=15`.
- Add `evals/human_review/` sheet format (versioned rubric dimensions matching the judge; pass/fail + free-text).
- Blueprint sync (docs only under allowed v8.2/ADR paths used by this slice's design): record ADR-007 for evaluation gates/tolerances/replay CI strategy; clarify that §11.2 ≥24 cases / ≥3 destinations remains the Slice 2 exit checklist item and is not expanded inside 2.5/2.6 path cells; note that unmeasured §11.4 bands cannot gate until a later measurement change fills them.
- No **BREAKING** HTTP, SSE, or persisted-trip change. Judge off leaves generate unchanged.

## Capabilities

### New Capabilities

- `eval-regression-gate`: quarantine exclusion from the gate, named baseline diffs, tolerance bands for measured metrics only, explicit `--update-baseline`, and the seeded regression exit contract.
- `eval-offline-judge`: offline sampled judge via the LLM gateway, schema-validated judgments, prompt/rubric versions, `judge_unavailable` on failure, and isolation from deterministic scoring and the request path.
- `eval-human-review`: versioned human-review sheet format under `evals/human_review/` aligned with judge dimensions (§11.7).

### Modified Capabilities

- `eval-golden-harness`: the runner's gate behavior changes (quarantine exclusion, named diffs, tolerance reporting). Schema v2, assertion keys, `score_case`, `--replay`, and `--fixtures-only` stay as 2.1–2.4 left them unless a gate rule above requires a report field.
- `eval-deterministic-metrics`: metrics may be called from the gate report/diff. They remain pure and still MUST NOT change assertion keys or how `score_case` decides pass/fail for a single case.
- `github-actions-ci`: add a PR/main replay eval-gate job and a scheduled live eval job; Phase A pytest/docker non-deploy guarantees stay.
- `s0-decision-records`: add ADR-007 (evaluation gates, tolerances, replay CI) consistent with §21 / §11.

## Impact

- **Work surface, in order:** 2.5 `scripts/run_evals.py`, `evals/baselines/**` (only via explicit update or tolerance metadata), `.github/workflows/**`, gate tests under `tests/evaluation/**`; then 2.6 `src/evaluation/judge/**`, `evals/human_review/**`, `src/config.py` + `.env.example` for judge settings, `tests/evaluation/` judge tests. Architecture G11 already lists `EVALUATION_JUDGE_ENABLED` default false when the field exists.
- **Call sites outside a row path cell:** `src/config.py` / `.env.example` for `EVALUATION_JUDGE_ENABLED` and `EVALUATION_JUDGE_TIMEOUT_SECONDS` (rollback is flag off; G3 forbids `os.environ`). `tests/evaluation/**` holds gate and judge tests the verify commands name. `docs/v8.2/adr/` for ADR-007. The PR eval job may need a Qdrant service because `--replay` still calls `PlannerService.generate`; the existing pytest job stays without Qdrant.
- **Reuse, do not redefine:** `LLM_REPLAY_MODE` / `use_llm_replay`, `evals/replay/**`, `score_case`, the eight metrics in `src/evaluation/metrics/`, golden schema v2, and the twelve Darjeeling cases.
- **No new package.** No provider SDK import outside `src/core/llm/client.py`. No HTTP evaluation endpoints. No request-path judge. No migration.
- **Resilience:** judge timeout uses `EVALUATION_JUDGE_TIMEOUT_SECONDS`; judge failure records `judge_unavailable` and leaves deterministic gate/results unchanged. Replay miss still fails the eval job with `replay_miss`. Live nightly flakiness does not fail PR CI (§11.1).
- **No impact on:** planner generate with judge off, SSE names, trip persistence, travel engine source, golden case assertion keys, and Slice 3+ feature flags.
- **Downstream:** Slice 3+ behavior changes use this gate. Slice 5.4 may add retrieval recall into the gate when labels exist. Slice 7 may promote the judge only after §11.8. Expanding to ≥24 cases / ≥3 destinations is a separate follow-on toward the Slice 2 exit checklist.

## Non-goals

- No expansion of the golden set to Manali/Goa/sparse town inside this change (Slice 2 exit item; not in 2.5/2.6 path cells).
- No wiring of unmeasured latency/token/cost/coherence variance as hard CI fails.
- No blending of judge scores into the deterministic gate number (§11.1).
- No advisory or in-path judge; no repair triggers (N9 / ADR-004 / Slice 7).
- No change to `score_case` assertion keys or to `src/travel_engine/**`.
- No new LiteLLM import outside the gateway (row 2.6 stop condition).
- No edit to `docs/context.md` inside apply unless the completing PR's §19 report policy requires it after green verify (same pattern as prior v83 slices: prefer PR description).

## Constraints

From `AGENT.md` and the v8.3 invariants, this change must:

- Keep `litellm` imported only in `src/core/llm/client.py`.
- Read flags through `get_settings()`. Scripts must not call `os.environ`.
- Keep the judge off the request path; planner/tools must not import `src.evaluation.judge`.
- Keep metric functions free of LLM/network/DB I/O; judge I/O goes only through the gateway.
- Apply 2.5, then 2.6. 2.6 failure must not change 2.5 gate exit codes.
- Add no package. Defaults keep today's generate behavior.

Blueprint path notes, confirmed against the checkout:

- `evals/replay/**` and metrics already exist from 2.2–2.3. Baseline is still case pass/fail only (`evals/baselines/darjeeling.json`).
- Quarantine is loaded but not excluded from the gate (deferred from 2.1 by design).
- `EVALUATION_JUDGE_ENABLED` is already in G11's expected defaults map but is not yet a `Settings` field.
- CI has no eval job and no Qdrant service today.
- ADR-007 is named in the blueprint §21 table and is not on disk yet.
