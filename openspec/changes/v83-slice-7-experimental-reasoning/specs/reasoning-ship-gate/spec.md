## Purpose

Decides whether the reasoning layer may be enabled later by comparing it with the current planner, and records that decision without turning the flag on in this change.

## ADDED Requirements

### Requirement: Ship comparison is a replay diff against the current planner
The repository MUST provide a comparison entry point that runs the existing golden itinerary cases twice in replay mode: once with `REASONING_LAYER_ENABLED` false and the sample rate 0, and once with the layer flag true. It MUST score both with the existing deterministic gates. It MUST report LLM call count, token totals, and fallback or skip rate for the reasoning roles. It MUST NOT call a live provider when replay mode is on. It MUST NOT pass `--update-baseline` and MUST NOT rewrite the itinerary baseline files. A missing replay fixture MUST fail that treatment case with a named fixture error rather than a silent live call.

#### Scenario: Replay comparison does not update the baseline
- **WHEN** the comparison entry point runs in replay mode
- **THEN** it writes a report and leaves the existing golden baseline files unchanged

#### Scenario: A missing treatment fixture fails closed
- **WHEN** replay mode is on and a treatment case has no fixture for the reasoner call
- **THEN** that case is reported as a fixture miss and the provider is not called

### Requirement: The human margin is pre-registered and missing evidence fails closed
ADR-013 MUST record the margin before treatment numbers are filled in: human-rated quality improves by at least 10 percentage points pass rate, or by at least 0.3 on a 5-point scale, and the confidence interval excludes zero. The comparison MUST use only human-review sheets that already exist in the repo. It MUST NOT invent reviewer scores. If no paired human review of control versus treatment exists, clause 2 of the ship gate MUST be recorded as not met.

#### Scenario: No human pairs means clause 2 fails
- **WHEN** the comparison runs and the human-review directory has no paired control and treatment scores
- **THEN** the report marks the human-margin clause not met and does not synthesize scores

### Requirement: ADR-013 records stay-off unless every ship clause passes
The repository MUST add `docs/v8.2/adr/013-reasoning-layer-ship.md` with context, decision, alternatives, consequences, migration and rollback, and status. The decision MUST be stay off unless the report shows all of the following: every §11.3 deterministic gate still passes, the pre-registered human margin is met, generate p95 is at most 45 seconds, token and cost deltas are within the §4 bounds that are actually measured, and the failure or fallback rate is no worse than the control. An unmeasured §4 cell MUST NOT be treated as passed. `REASONING_LAYER_ENABLED` MUST remain false in settings and in `.env.example` even when the ADR says the evidence would support a later enablement. Rollback text MUST say to set the layer flag false and the sample rate to 0.

#### Scenario: Unmeasured cost does not ship the layer
- **WHEN** the deterministic gates pass and the §4 cost cell is still `[SET IN S0]`
- **THEN** ADR-013 decides stay off and the layer flag default remains false

#### Scenario: A failed gate stays off
- **WHEN** the treatment run publishes a trip with a critical finding
- **THEN** ADR-013 decides stay off and does not set the layer flag true
