## ADDED Requirements

### Requirement: ADR-007 records evaluation gates and tolerances
The repository SHALL contain an accepted decision record at `docs/v8.2/adr/007-evaluation-gates.md` with context, decision, alternatives, consequences, migration and rollback, and status `accepted`. The record MUST state that deterministic case pass/fail for non-quarantined cases gates releases, that tolerance-banded metrics gate only when S0 measured variance exists, that CI PRs use replay while live runs are scheduled and do not block PRs on flakiness, that baselines change only via explicit `--update-baseline` in a reviewed PR, and that the offline judge informs and does not gate until §11.8 promotion. The record MUST state that expanding the golden set to §11.2 minimums (≥24 cases, ≥3 destinations) remains a Slice 2 exit checklist item outside rows 2.5 and 2.6 path cells.

#### Scenario: Record exists and is accepted
- **WHEN** subslices 2.5 and 2.6 are complete
- **THEN** `docs/v8.2/adr/007-evaluation-gates.md` exists and its status is `accepted`

#### Scenario: Unmeasured bands cannot gate
- **WHEN** the record states how tolerance bands apply
- **THEN** it says a metric without measured baseline variance cannot hard-fail the gate

#### Scenario: Judge stays inform-only here
- **WHEN** the record states the judge role for this slice
- **THEN** it says the offline judge does not gate and does not run on the request path

#### Scenario: Case expansion stays a checklist item
- **WHEN** the record states golden-set size
- **THEN** it says ≥24 cases across ≥3 destinations is still required for Slice 2 exit and is not claimed done by shipping the gate runner alone
