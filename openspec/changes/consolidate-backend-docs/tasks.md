## 1. One copy of the v7 blueprint

- [x] 1.1 In `docs/blueprint_final.md`, delete from the `---------------` separator through end of file. Leave the v6.1 closing line. Add a short pointer that post-P7 steps live only in `docs/v2_blueprint.md`.
- [x] 1.2 Confirm `docs/v2_blueprint.md` is unchanged and still contains the V0–V6 body.

## 2. Label history and fix the session entry

- [x] 2.1 Add the three-line historical banner to `docs/steps/step0.md`, `step1.md`, `step2.md`, `step3.md`, `step4.md`, `step5.md`, `step5_critic.md`, `step6.md`, and `step7.md`. Each banner says the file is not the current build step and points at `docs/context.md`.
- [x] 2.2 Rewrite the opening read order in `docs/context.md` so a session goes to `AGENT.md`, `docs/app/system.md`, `docs/blueprint_final.md`, and `docs/v2_blueprint.md`. Add the living-vs-history map. Do not rewrite the progress table or the stub list. Bump **Last updated**.
- [x] 2.3 In `docs/app/documentation.md`, change the `docs/steps/` row so it says historical build prompts. In `docs/spec.md`, change the build-prompts row the same way. Do not refresh the manual module map.
- [x] 2.4 Replace the header of `docs/app/p2guide.md` so the next step is `docs/context.md`. Search that file for `P5.12` and retarget any remaining “this is next” sentence at `docs/context.md`. Do not rewrite the interview Q&A.

## 3. VPS note and OpenSpec context

- [x] 3.1 Replace the terminal transcript at the top of `docs/vps.md` with a short baseline (about 1 GB RAM, 2 GB swap, amd64, UFW 22/80/443, baseline done). Leave `## Application hosting` and `## Geo upstream troubleshooting` in place, including the canonical hosts and the pointer to `docs/steps/blueprint_production.md` and `ops/`.
- [x] 3.2 In `openspec/config.yaml` `context:` only, set the phase to post-P7 / v7 and point authors at `docs/context.md`. Remove the instruction to open `docs/steps/step*.md` as the current step and the sentence that says the phase is P1. Leave the architecture rules in place.

## 4. Remove noise files

- [x] 4.1 Delete `docs/update.md`, `docs/fe_suggestins.md`, `docs/front_blueprint_2.md`, `docs/steps/Blueprint.md`, and `docs/operations/deployment.md`, `monitoring.md`, `cost.md`, `incidence-response.md`, `backup.md`, and `rollback.md`.
- [x] 4.2 In living docs only (`docs/` excluding nothing already deleted, plus `openspec/config.yaml`), grep for `update.md`, `fe_suggestins`, `front_blueprint_2`, `docs/operations/`, and `steps/Blueprint.md`. Fix any remaining pointer so it does not treat those paths as present. Do not edit archived OpenSpec changes. Do not edit `src/`.

## 5. Proof

- [x] 5.1 Confirm `docs/blueprint_final.md` has no second `# Wandr — Backend Blueprint v7.0` heading, `docs/v2_blueprint.md` still has it, the nine step files start with the history banner, the noise paths are gone, and `docs/vps.md` still names `api.explorai.online` and `docs/steps/blueprint_production.md`.
