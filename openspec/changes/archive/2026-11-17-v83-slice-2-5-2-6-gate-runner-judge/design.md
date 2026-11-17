## Context

See proposal.md for why rows 2.5 and 2.6 are one change. Behavior contracts are the delta specs under `specs/`.

Today `scripts/run_evals.py` scores every loaded case (including quarantined), diffs only pass→fail, prints `REGRESSION <id>: ...` already in one form, and exits non-zero on regression. `--update-baseline` already writes the baseline. There is no tolerance metadata, no CI eval job, no `src/evaluation/judge/`, and no `evals/human_review/`. Metrics exist in `src/evaluation/metrics/` but are unused by the runner. Replay fixtures exist under `evals/replay/`. CI pytest has PostGIS and no Qdrant. G11 already expects `EVALUATION_JUDGE_ENABLED` default false when the Settings field exists. ADR-004 allows an offline S2 judge scaffold off the request path. ADR-007 is named in the blueprint and missing on disk. S0 left latency/token/cost/coherence variance unmeasured.

## Goals / Non-Goals

**Goals:**

- One gate path that excludes quarantined cases, names regressions, and never silently rewrites baselines.
- Tolerance metadata that hard-fails only measured bands; unmeasured metrics stay report-only.
- PR CI that runs `--replay`; nightly live that does not block PRs.
- Offline judge + human-review sheet that share dimensions and cannot affect the deterministic exit code.
- ADR-007 capturing those rules and the §11.2 case-count follow-on.

**Non-Goals:**

- Growing the golden set to Manali/Goa inside this change.
- Inventing measured latency/coherence variances so those bands can hard-fail today.
- Promoting the judge to advisory or repair (Slice 7 / §11.8).
- Changing `score_case` assertion keys or travel_engine behavior.

## Decisions

### 1. Apply order is 2.5, then 2.6

Finish gate runner + CI + ADR-007 before judge/human-review. Judge failure tests must show the 2.5 exit code unchanged. Do not start section 2.6 tasks until the seeded regression and replay CI path are green.

Alternative considered: two OpenSpec changes. Rejected because the user asked for one batch in order, matching the 2.2–2.4 precedent.

### 2. Quarantine exclusion lives in the runner gate, not the loader

`load_golden_cases` keeps returning quarantined cases (2.1 contract). `_run_suite` / `_diff_baseline` compute:

- `gate_cases` = cases where `quarantined` is false
- `gate_pass_rate` over gate cases only
- regressions only among gate cases
- report fields: `pass_rate` (gate), `quarantined_cases` (list of scored quarantined results)

This matches §11.2 and the deferred note in the 2.1 design.

Alternative considered: loader skip. Rejected because 2.1 forbade it and quarantine tracking needs the case still loaded.

### 3. Named regression code stays `REGRESSION`

Keep the existing print prefix `REGRESSION` and require the case id on the same line. Seeded unit tests call the pure diff helper (extract if needed) with in-memory baseline/run dicts so the required test does not need a full planner generate. Full-script integration may still use `--fixtures-only` with a temp baseline.

Alternative considered: new codes per metric. Rejected for case pass/fail; metric band failures use a distinct `TOLERANCE <metric>` line so operators can tell them apart.

### 4. Tolerance metadata is a committed JSON beside baselines

Add `evals/baselines/tolerances.json` (or per-destination `*.tolerances.json`) listing only metrics with measured variance. Initial commit may be an empty object or only pass-rate identity (no band). The runner loads it; missing/unlisted metrics are report-only. Do not invent S0 numbers. When a later measurement change fills variance, it updates this file in a reviewed PR with `--update-baseline` as needed.

Gate-callable aggregates from existing metrics (e.g. duplicate rate / feasibility over fixture itineraries) may be attached to the report in 2.5 when cheap to compute from the generation result already in hand. Do not call the judge from the gate.

Alternative considered: hard-coding §11.4 absolute thresholds (0.95 location, 0.80 recall) now. Rejected for metrics that need labels or V2 location types the suite does not yet assert; those wait for Slice 3/5.4.

### 5. PR eval-gate job gets the services `--replay` needs

`--replay` still calls `PlannerService.generate` (LLM served from fixtures). That path ensures Qdrant and embeddings today. Add a dedicated `eval-gate` job (same `ci.yml` or a sibling workflow triggered on the same events) with PostGIS + Qdrant services, empty `LLM_API_KEY`, and `python scripts/run_evals.py --destination darjeeling --replay`. Keep the existing pytest job without Qdrant so unit CI stays light.

Nightly: `schedule` cron workflow running without `--replay` when `LLM_API_KEY` secret is present; otherwise skip with a message. Nightly failure must not be a `check` required on PRs.

Alternative considered: PR gate uses `--fixtures-only` only. Rejected because the blueprint row and §11.1 require replay on CI; fixtures-only remains available locally and for unit tests.

Alternative considered: commit generate outputs as fixtures and skip PlannerService in CI. Rejected for this slice; that would redefine the 2.2 replay contract.

### 6. Judge scaffold is a small offline package behind the flag

Add:

- `Settings.EVALUATION_JUDGE_ENABLED: bool = False`
- `Settings.EVALUATION_JUDGE_TIMEOUT_SECONDS: int = 15`
- `.env.example` lines beside other eval settings
- `src/evaluation/judge/` with prompt version, rubric version, schema parse, and a `judge_case` (name flexible) that calls `chat_completion` / structured response through the gateway only
- Closed dimensions initially: `relevance`, `diversity`, `narrative` (inform-only preference/quality per §11.5)
- Sample rate or max-n argument on the offline entry (CLI flag or function arg); default sample is small (e.g. 1) so enabling the flag in tests does not fan out

Do not call the judge from `scripts/run_evals.py` gate path by default. Optional `--judge` later is fine if it cannot change the deterministic exit code; prefer a separate function invoked only from judge tests in this slice to keep 2.5 exit semantics obvious.

Architecture: add a test that planner/tools/routers/travel_engine do not import `src.evaluation.judge`. G11 will assert the new flag default when the field exists; do not edit `_helpers.py` unless a new non-§7.1 name appears (it should not).

Stop if a new provider SDK import outside the gateway is required.

### 7. Human-review sheet shares the dimension list

`evals/human_review/README.md` (or schema JSON) plus an example sheet. Validation is pure Python in the judge or a tiny shared constants module under `src/evaluation/judge/dimensions.py` (or `src/evaluation/rubric.py` if both need it without circular imports). Same three dimensions + free-text + rubric_version + reviewer_id.

Full §11.7 (≥60 trips, ≥2 reviewers) is protocol documentation, not a dataset this slice must populate.

### 8. Blueprint sync via ADR-007 only

Write `docs/v8.2/adr/007-evaluation-gates.md`. Do not edit `docs/steps/wandr_blueprint_version8.md` in apply unless a later user asks; the ADR records the operational clarifications (unmeasured bands, case-count follow-on, replay CI vs nightly live). Update `s0-decision-records` via the delta spec.

### 9. Resilience

- Replay miss: existing `replay_miss` fails eval-gate.
- Judge timeout: respect `EVALUATION_JUDGE_TIMEOUT_SECONDS`; on timeout/error record `judge_unavailable`; deterministic exit unchanged.
- Live nightly without secrets: skip, do not fake judgments or itineraries.
- Baseline update: only `--update-baseline`; CI jobs never pass that flag.

## Risks / Trade-offs

- [Eval-gate job is slower/heavier than pytest because of Qdrant + generate under replay] → Keep it as a separate job so unit CI stays lean; cache pip; fail fast on `replay_miss`.
- [Empty tolerances mean few band hard-fails at first] → Acceptable: case regressions still gate; ADR-007 documents measured-only bands; later measurement PRs fill tolerances.
- [Judge schema/model drift] → Version prompt and rubric; invalid output is schema failure, not a silent pass.
- [CI generate needs destination data / embeddings that pytest does not] → Document required seed/index steps in the workflow; if the job cannot be made green without inventing data, stop and report (do not weaken to fixtures-only without an ADR update).

## Migration Plan

1. Ship 2.5 runner + tests + tolerances file + ADR-007 + CI jobs.
2. Confirm `python scripts/run_evals.py --destination darjeeling --replay` twice locally and in CI.
3. Ship 2.6 judge + human-review format + flag defaults.
4. Rollback: remove eval-gate/nightly jobs; set `EVALUATION_JUDGE_ENABLED=false`; revert runner gate logic if needed. Baselines remain recoverable from git.

## Open Questions

None that block specs or tasks. Embedding/index bootstrap details for the eval-gate job are settled during apply against the existing local eval runbook; if blocked, stop and report rather than inventing a fixtures-only PR gate.
