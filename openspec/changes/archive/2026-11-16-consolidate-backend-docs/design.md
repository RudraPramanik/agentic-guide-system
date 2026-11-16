## Context

See proposal.md — Why. `docs/blueprint_final.md` v6.1 ends at the “Structure from code” line, then a `--------------- / v2` separator, then a byte-for-byte copy of `docs/v2_blueprint.md`. `docs/operations/*.md` and `docs/steps/Blueprint.md` are empty. `docs/update.md` is a chat transcript. `docs/front_blueprint_2.md` is a retired pointer. `docs/fe_suggestins.md` is the pre-`FE_guide` brainstorm. `docs/context.md` and `openspec/config.yaml` still tell a session to open `docs/steps/step*.md` and, in config, still say the phase is P1. `docs/app/p2guide.md` still says the next step is P5.12. `docs/vps.md` is a shell transcript plus a real hosting section.

Specs that must stay true without a rewrite: `production-deployment-blueprint` (vps summary, hosts, geo note, pointer to `docs/steps/blueprint_production.md`), `frontend-dev-blueprint` (`docs/blueprint_frontend.md` + `docs/FE_guide.md`), and the developer-manual pages under `docs/manual/`.

## Goals / Non-Goals

**Goals:**

- One full copy of the v7 blueprint.
- A session that starts at `docs/context.md` cannot mistake a finished step prompt for the next task.
- Delete only files that are empty, duplicated, or already retired.

**Non-Goals:**

- Moving history into a new `docs/archive/` tree. That becomes a second shelf agents open.
- Refreshing the junior manual’s module map. The through-step marker is already P7 + V6.1.
- Editing `src/` or ops scripts. No external I/O, so no new timeout or fallback contract. `travel_engine` is untouched.

## Decisions

### Delete noise; keep history in git

Delete `docs/update.md`, `docs/fe_suggestins.md`, `docs/front_blueprint_2.md`, `docs/steps/Blueprint.md`, and every file under `docs/operations/`. Git history is the archive.

Alternative considered: move them to `docs/archive/`. Rejected because a folder of “old but present” docs is how the second FE blueprint and the v7 paste survived.

### Strip the v7 paste, do not merge the files

Delete `docs/blueprint_final.md` from the `---------------` separator through EOF. Leave the v6.1 ending and a short pointer: post-P7 steps are only in `docs/v2_blueprint.md`. The pasted region matches `docs/v2_blueprint.md` exactly, so nothing unique is lost.

Alternative considered: make `docs/v2_blueprint.md` a pointer and keep v7 inside `blueprint_final.md`. Rejected because context, system, and the v7 file itself already name `docs/v2_blueprint.md` as the post-P7 SSOT.

### Banner the step prompts; do not delete them

Add a three-line banner to `docs/steps/step0.md`–`step7.md` and `docs/steps/step5_critic.md`: historical, not the current step, checkpoint is `docs/context.md`. OpenSpec specs and the progress table still cite these files. Deleting them would break those citations.

`docs/steps/step5_critic.md` already says not to re-apply it. The banner still has to point at `docs/context.md` so it matches the other step files.

### One map, in the checkpoint

Put the living-vs-history map in the header of `docs/context.md`. Update the matching row in `docs/spec.md` and the “does not replace” row in `docs/app/documentation.md` so those indexes do not still call `docs/steps/` the current build prompts. Do not add a new top-level doc for the map.

### Study guide: header only

Replace the header block of `docs/app/p2guide.md` (through the “knowledge, not a paste prompt” paragraph) so “next” is `docs/context.md`. Do not edit the interview body in this change. Stub callouts deeper in the file that still say search or the planner is unbuilt are out of scope unless a header-only fix leaves the file claiming P5.12 is next. If a later section repeats “next is P5.12”, change that sentence to point at `docs/context.md` and stop. Do not rewrite Q&A.

### VPS note: keep the SOP, drop the transcript

Replace `docs/vps.md` above `## Application hosting` with a short baseline: about 1 GB RAM, 2 GB swap, amd64, UFW allows 22/80/443, baseline already done. Leave the application-hosting section and the geo troubleshooting section as they are, including the canonical hosts and the pointer to `docs/steps/blueprint_production.md` and `ops/`.

### OpenSpec context block

In `openspec/config.yaml` `context:` only, change the session read order and the “Current phase: P1” sentence. Keep the architecture rules and the “do not backfill the blueprint into specs” rule. New wording: phase is post-P7 / v7; read `docs/context.md` for done vs stub; do not treat `docs/steps/step*.md` as the current task.

## Risks / Trade-offs

- [A deleted chat (`docs/update.md`) is the only write-up of an early Geoapify idea] → The shipped contract is `PLACES_SOURCES` in `docs/context.md` and `docs/steps/blueprint_production.md`. Git still has the transcript.
- [A step banner hides a prompt someone still wants to re-read] → The file stays; the banner only changes how it is framed.
- [Trimming `docs/vps.md` drops a command that was only in the transcript] → Hosting commands already live in the section that stays and in `docs/steps/blueprint_production.md`.
- [Header-only p2guide leaves a stale sentence in the body] → The apply task searches the file for `P5.12` and retargets those lines at `docs/context.md` without rewriting the teaching sections.
- [Dangling links to deleted files] → After deletes, grep `docs/` and `openspec/config.yaml` for the removed paths and fix living pointers. Archived OpenSpec changes may still mention the old names; leave those archives alone.

## Migration Plan

1. Strip the v7 paste and add banners and the context map before deleting files, so pointers exist first.
2. Delete the noise files.
3. Grep living docs for the removed paths.
4. Rollback is `git checkout` of `docs/` and `openspec/config.yaml`. No migration, no deploy.

## Open Questions

None. The keep/delete split is fixed in the specs.
