## Why

`guideagent/docs` now mixes living sources of truth with empty files, a chat dump, retired drafts, and a second full copy of the v7 blueprint pasted onto the end of `docs/blueprint_final.md`. Agents and people open the wrong file and treat finished build prompts as current work. P0–P7 and v7 V0–V6.1 are already shipped, so the tree should say what to read now.

## What Changes

- Remove files that carry no living contract: the chat dump `docs/update.md`, the empty `docs/operations/*.md` set, the empty `docs/steps/Blueprint.md`, the retired FE pointer `docs/front_blueprint_2.md`, and the brainstorm `docs/fe_suggestins.md`.
- Cut the duplicated v7 body out of `docs/blueprint_final.md` (everything after the v6.1 closing line) and leave a short pointer to `docs/v2_blueprint.md`.
- Rewrite the session read order in `docs/context.md` and `openspec/config.yaml` so the current path is context → `AGENT.md` → `docs/app/system.md` / the two blueprints. `docs/steps/step*.md` stays on disk as history, with a banner that it is not the next build step.
- Fix the header of `docs/app/p2guide.md` so it no longer says the next step is P5.12. Point readers at `docs/context.md`.
- Replace the raw terminal transcript at the top of `docs/vps.md` with a short baseline summary. Keep the application-hosting and geo notes that operators still use.
- Add one living-doc map (in `docs/context.md`) that names the files to trust and the files that are history.

### Non-goals

- No edits under `src/`, tests, Compose, Dockerfiles, or run scripts.
- No rewrite of `docs/blueprint_final.md` v6.1 content, `docs/v2_blueprint.md`, `docs/FE_guide.md`, `docs/blueprint_frontend.md`, `docs/app/system.md`, or `docs/app/lld.md`.
- No deletion of `docs/steps/step0.md`–`step7.md`, `docs/steps/step5_critic.md`, `docs/manual/`, `docs/books/`, `docs/spec.md`, `docs/issue_solve.md`, `docs/next_version.md`, `docs/ci_cd_plan.md`, or `docs/steps/blueprint_production.md`.
- No new endpoints, env vars, or packages. Evaluation HTTP and `src/auth/dependencies.py` stay stubs as recorded in `docs/context.md`.
- Not a numbered `docs/steps/step*.md` build step.

`AGENT.md` still applies: docs-only, no architecture change. No conflict with the blueprints; this removes a duplicate, it does not change a locked design.

## Capabilities

### New Capabilities

- `docs-housekeeping`: Which `guideagent/docs` files are living sources of truth, which stay as labeled history, and which must be absent.

### Modified Capabilities

- `planner-blueprint-sot`: `docs/blueprint_final.md` remains the P0–P7 master and must not also contain the v7 blueprint body.
- `developer-manual`: The session entry (`docs/context.md`) must not send readers to `docs/steps/step*.md` as current work.
- `p2-study-guide`: The study-guide header must follow `docs/context.md` for “what’s next,” not a finished phase.

## Impact

- Docs only, plus the OpenSpec project-context block in `openspec/config.yaml` (it still says phase P1 and “read the current step file”).
- No API, schema, or dependency change.
- Existing main specs that require `docs/vps.md`, `docs/blueprint_frontend.md`, `docs/FE_guide.md`, and `docs/app/documentation.md` stay satisfied; those files remain.
