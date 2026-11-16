## ADDED Requirements

### Requirement: Session entry does not treat finished step prompts as current work

`docs/context.md` MUST remain the session checkpoint and MUST still link to the developer manual (`docs/app/documentation.md` → `docs/manual/`). Its opening read order MUST name `AGENT.md`, `docs/app/system.md`, `docs/blueprint_final.md` for P0–P7, and `docs/v2_blueprint.md` for post-P7. It MUST include a short map that labels `docs/steps/step*.md` as history. It MUST NOT instruct the reader to open a `docs/steps/step*.md` file as the current build step. The manual index `docs/app/documentation.md` MUST describe `docs/steps/` as historical build prompts, not as the place to find the next task.

#### Scenario: Agent starts a session

- **WHEN** a reader follows the opening of `docs/context.md`
- **THEN** they are sent to the checkpoint, guardrails, architecture, and the two blueprints, and the step prompts are labeled history

#### Scenario: Junior opens the manual index

- **WHEN** a reader opens the “what this manual does not replace” table in `docs/app/documentation.md`
- **THEN** `docs/steps/` is described as historical, and `docs/context.md` remains the place for what is done and what is next
