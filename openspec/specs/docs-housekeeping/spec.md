## Purpose

Keep `guideagent/docs` to one living set of sources of truth, a labeled history, and no empty or retired files that compete with them.

## Requirements

### Requirement: Living docs stay in place

The repository MUST keep these files as the living documentation set: `docs/context.md`, `docs/blueprint_final.md`, `docs/v2_blueprint.md`, `docs/app/system.md`, `docs/app/lld.md`, `docs/app/documentation.md`, `docs/manual/01-orientation.md` through `docs/manual/06-maintenance.md`, `docs/FE_guide.md`, `docs/blueprint_frontend.md`, `docs/steps/blueprint_production.md`, `docs/ci_cd_plan.md`, `docs/next_version.md`, `docs/spec.md`, `docs/issue_solve.md`, `docs/vps.md`, `docs/app/p2guide.md`, and `docs/books/README.md` plus `docs/books/p2-references.md`. This change MUST NOT rewrite their technical contracts except for the pointer, banner, header, and read-order edits named in the sibling requirements of this change.

#### Scenario: Reader looks for the current backend contract

- **WHEN** a reader or agent needs current architecture, the P0–P7 build contract, the post-P7 build contract, the FE wire contract, or the production SOP
- **THEN** those documents are still present at the paths above

### Requirement: Finished build prompts stay as labeled history

`docs/steps/step0.md`, `docs/steps/step1.md`, `docs/steps/step2.md`, `docs/steps/step3.md`, `docs/steps/step4.md`, `docs/steps/step5.md`, `docs/steps/step5_critic.md`, `docs/steps/step6.md`, and `docs/steps/step7.md` MUST remain. Each MUST open with a banner that the file is historical, that it is not the current build step, and that `docs/context.md` is the checkpoint. `docs/context.md` MUST NOT tell a new session to open `docs/steps/step*.md` as the current step.

#### Scenario: New session starts from context

- **WHEN** a reader opens the top of `docs/context.md`
- **THEN** the read order points at `AGENT.md`, `docs/app/system.md`, and the two blueprints, and does not instruct them to implement the next `docs/steps/step*.md`

#### Scenario: Someone opens an old step prompt

- **WHEN** a reader opens any `docs/steps/step*.md` file listed above
- **THEN** the banner states the file is history and points at `docs/context.md`

### Requirement: Noise files are absent

The following paths MUST NOT exist after this change: `docs/update.md`, `docs/steps/Blueprint.md`, `docs/front_blueprint_2.md`, `docs/fe_suggestins.md`, `docs/operations/deployment.md`, `docs/operations/monitoring.md`, `docs/operations/cost.md`, `docs/operations/incidence-response.md`, `docs/operations/backup.md`, and `docs/operations/rollback.md`. Living docs MUST NOT link to those paths as if the files were still present.

#### Scenario: Reader searches for retired drafts

- **WHEN** a reader looks for a second FE blueprint, the FE brainstorm, an operations runbook under `docs/operations/`, or `docs/update.md`
- **THEN** those files are gone, and the living FE contract remains `docs/FE_guide.md` plus `docs/blueprint_frontend.md`

### Requirement: VPS notes are a summary, not a terminal log

`docs/vps.md` MUST summarize the completed VPS baseline (memory, swap, architecture, and UFW ports 22/80/443) and MUST keep the application-hosting steps and geo-upstream troubleshooting that point at `docs/steps/blueprint_production.md` and `ops/`. It MUST NOT embed the raw terminal transcript, and it MUST NOT embed secrets. It MUST still name the canonical hosts `https://explorai.online`, `https://www.explorai.online`, and `https://api.explorai.online`.

#### Scenario: Operator opens the VPS note

- **WHEN** a reader opens `docs/vps.md`
- **THEN** they see a short baseline summary plus the hosting and geo sections, and they do not see a shell session dump

### Requirement: OpenSpec project context matches the shipped phase

The project context in `openspec/config.yaml` MUST describe the phase as post-P7 / v7 and MUST tell artifact authors to read `docs/context.md` for what is done. It MUST NOT say the current phase is P1, and it MUST NOT tell authors to open `docs/steps/step*.md` as the current build step.

#### Scenario: A new change reads project context

- **WHEN** OpenSpec injects project context into a new artifact
- **THEN** that context does not claim the backend is still on P1 or that the next work is a `docs/steps/step*.md` prompt
