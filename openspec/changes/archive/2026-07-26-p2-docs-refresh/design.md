## Context

P2 implementation and verification are done (`context.md` → Next step P3.1; steps 2.9/2.10 ✅). The developer manual index still says **Through step: P2.8** and lists pytest/smoke as not built. `docs/app/p2guide.md` still says geo/destinations/places are stubs and “You are here” as if P2 is in progress. `system.md` / `lld.md` are architecture essays and are mostly still accurate; they need only drift fixes, not a rewrite.

Constraints: docs-only; keep tables over prose; never invent stub APIs; readiness language must match formula-true floors from the archived P2 verification change.

## Goals / Non-Goals

**Goals:**
- Bring the developer manual through P2.10 and log the phase-complete refresh.
- Correct `p2guide.md` so engineers/interview readers see P2 as shipped.
- Fix any concrete factual drift in `system.md` / `lld.md` found during the pass.

**Non-Goals:**
- Application code, tests, migrations, or OpenSpec archive of this change (separate).
- Rewriting `step2.md` or `context.md`.
- Expanding `system.md` into a phase changelog.
- Documenting unbuilt P3+ APIs as if real.

## Decisions

1. **Manual is the cadence deliverable; p2guide is a separate capability**  
   - Why: `06-maintenance.md` already owns the phase-end trigger for `documentation.md` + `docs/manual/*`. `p2guide.md` is interview/engineering knowledge and was never covered by that cadence — it still needs an explicit sync so it does not contradict `context.md`.  
   - Alternative: fold p2guide into the manual refresh only — rejected because different audience and no TOC link requirement.

2. **Truth source = `docs/context.md` + archived P2 verification specs**  
   - Copy real-vs-stub and live endpoints from context; copy readiness volume-vs-score floors from `destination-readiness` / `p2-verification` main specs.  
   - Alternative: re-derive floors from `step2.md` alone — risk of reintroducing the stale `place_count >= 50 ⇒ limited` language.

3. **`system.md` / `lld.md` = opportunistic corrections only**  
   - Scan for “stub”, wrong next-phase, or missing geo/destinations statements that contradict P2-complete reality. Do not add long “P2 complete” sections.  
   - Alternative: full system.md phase status section — rejected as churn vs architecture-essay role.

4. **Do not bump `context.md` except if a link/path typo is found**  
   - Context already records P2 complete; this change is the deferred manual refresh it points at.

## Risks / Trade-offs

- [Manual over-edit] → Stick to checklist in `06-maintenance.md`; prefer row updates over new essays.  
- [Readiness floor drift returns] → Explicitly state volume floor ≥50 vs limited-band ≥100 (preferred) / ≥88 minimum in recipes and snapshot.  
- [p2guide becomes a second context.md] → Keep engineering/interview Q&A; replace only the “stubs / you are here / target endpoints” framing with “shipped / next is P3”.

## Migration Plan

Docs-only PR/session: edit files → sanity checklist in `06-maintenance.md` → no rollback beyond git revert.

## Open Questions

None — scope is documentation sync after a completed phase.
