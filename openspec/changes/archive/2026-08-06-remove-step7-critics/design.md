## Context

P7.0 code is shipped; `docs/steps/step7.md` v2.1 is the build contract. `docs/step7_critics.md` remains a 1000-line review draft that duplicates (and partially contradicts superseded) guidance. Project rule: one SoT per step under `docs/steps/`.

## Goals / Non-Goals

**Goals:**
- Delete `docs/step7_critics.md`.
- Remove live references from `step7.md` and `p7-step7-build-contract`.
- Leave lock content in step7.md unchanged.

**Non-Goals:**
- P7.1+ implementation; rewriting Decision/Fix Log; deleting archive artifacts; `docs/context.md` Progress changes.

## Decisions

### D1 — Delete, don’t relocate
- **Choice:** Remove the file from `docs/`; do not move to `docs/archive/` or rename.
- **Why:** Git + OpenSpec archive already preserve history; a relocated copy still risks agent discovery.
- **Alternatives:** Keep as “historical” with a banner — rejected (SoT pollution).

### D2 — Spec wording after delete
- **Choice:** MODIFY build-contract requirement to state step7.md is the **sole** P7 Cursor build contract under `docs/`; remove the “choose between step7 and critics” scenario; add a scenario that `docs/step7_critics.md` MUST NOT exist (or MUST NOT be present as an alternate contract).
- **Why:** Spec currently assumes the critics file exists.

### D3 — Header edit only on step7
- **Choice:** Drop the two-line “Historical review notes → step7_critics” pointer; keep OpenSpec change attribution.
- **Why:** Minimal diff; locks stay intact.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Someone wants critic prose later | `git log` / archive `harden-p7-step7-prompt` |
| Stale links in archive markdown | Leave archives immutable |

## Migration Plan

1. Apply: delete file + edit step7 header + sync/apply delta to main `p7-step7-build-contract`.
2. Grep repo (excluding `openspec/changes/archive`) for `step7_critics` → expect zero live refs.
3. Rollback: restore file from git.

## Open Questions

None.
