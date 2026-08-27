## ADDED Requirements

### Requirement: Live runs gate ranking cutovers
When the golden harness is used as a gate for place-ranking or collection cutover (including hybrid V5), operators MUST run it in live pipeline mode (LLM key set; not `--fixtures-only`) so cases exercise real retrieval. Fixtures-only runs remain valid for offline/CI smoke and deterministic scorer checks, but MUST NOT alone satisfy a ranking-cutover gate. Each case result in the run report MUST continue to record whether it used `fixture` or live generate mode.

#### Scenario: Live cutover gate uses generate mode
- **WHEN** the harness is run as the V5 hybrid cutover gate with `LLM_API_KEY` set and without fixtures-only
- **THEN** case results report live generate mode (not `fixture`) and the command exit code reflects baseline regression rules

#### Scenario: Fixtures-only remains available offline
- **WHEN** the runner is invoked with fixtures-only or with an empty LLM key and fixtures present
- **THEN** cases still score from fixtures, reports mark `fixture` mode, and the run MAY exit 0 — without claiming cutover-gate closure by itself

#### Scenario: Mode is visible in reports
- **WHEN** a run report is written under `evals/runs/`
- **THEN** each case entry includes a mode field distinguishing fixture replay from live generate
