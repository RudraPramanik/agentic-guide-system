## Why

Blueprint v8.3 (`docs/steps/wandr_blueprint_version8.md` §9, subslice **0.1**) is the first implementation step, and it forbids treating any unshipped module, flag, or endpoint as already present. Later slices (run tracking, the eval gate, location, the engine, canonical trips, guidebook enrich) need one checked map of the checkout before any behavior change. That map does not exist yet.

## What Changes

- Add `docs/v8.2/repository_audit.md` as the Slice 0 repository-truth audit.
- Record a status matrix for the areas v8.3 will touch: `implemented-tested`, `implemented-untested`, `partial`, `stub`, or `deferred`, each row linked to a file, a symbol, and a test (or an explicit "no test").
- Inventory `Settings` in `src/config.py` against `.env.example`, and mark every v8.3 flag and proposed setting as absent until the code shows otherwise.
- Map the frontend map/guide integration and the planner SSE lifecycle from `docs/FE_guide.md` and the code that actually emits events.
- Record today's display-only stay and photo surfaces so Slice 9 does not treat them as lodging or place media: `accommodation_label`, the trip-page copy "Stays are unavailable", and whatever the stop cards actually render (the blueprint's "gradient stop cards" phrase is a claim to verify, not a fact to copy).
- Keep a contradiction log inside the same file. A blueprint claim that disagrees with the checkout is recorded, and the audit continues. ADR-001 through ADR-004 stay in subslice 0.4.

No production behavior changes. No **BREAKING** changes.

## Capabilities

### New Capabilities

(none — documentation only; no runtime behavior)

### Modified Capabilities

(none — `.openspec.yaml` sets `skip_specs: true`)

## Impact

- **Work surface:** guideagent docs only. The sibling frontend and `docs/FE_guide.md` are read as evidence and are not edited.
- **Files written:** `docs/v8.2/repository_audit.md` only (`docs/v8.2/**`).
- **No impact on:** application code, tests, migrations, settings, dependencies, HTTP paths, DTO shapes, SSE event names, Docker, or `docs/context.md`.
- **Downstream:** subslices 0.2–0.5 and Slices 1–9 cite this audit. They do not start from an unverified reading of the blueprint.

## Non-goals

- No application code, tests, migrations, settings, or frontend edits.
- No snapshots (0.2), baseline metrics (0.3), `[SET IN S0]` fill-in or ADR-001–ADR-004 (0.4), or architecture tests (0.5).
- No edits to `docs/steps/wandr_blueprint_version8.md`, `docs/context.md`, `docs/FE_guide.md`, or `docs/blueprint_final.md`.
- No new endpoints, flags, or packages. Proposed names in §7 and §8 stay proposed.
- No claim that `location_intelligence/`, `planner/runs/`, `geo/media/`, `planner_runs`, or Slice 9 lodging/media already exist. `docs/context.md` still describes post-P7 / v7 (V0–V6.1 done; V6.2/V6.3 deferred). Those v8 modules are absent until this audit finds them.

## Constraints

From `AGENT.md` and the v8.3 invariants, this subslice must:

- Stay inside `docs/v8.2/**`. Touching any other path is a stop.
- Not invent endpoints, DTO fields, or env vars. A name is "present" only with a file and symbol link.
- Not treat `docs/context.md` progress rows as proof. Each matrix row links to source or a test.
- Leave `travel_engine/` free of I/O claims it does not earn, and leave LLM access described as the existing gateway only.
- Not update `docs/context.md` here. The OpenSpec repo rule asks for a context update when a build step completes; subslice 0.1's allowed paths forbid that file. The audit is the record. A context pointer waits until a later subslice whose paths allow it.

Subslice 0.1's own stop column overrides the general halt in §18 item 1: a contradiction is logged and the audit continues. It does not open an ADR and it does not stop the rest of the matrix. §18 item 2 (suite already red) belongs to 0.2; this subslice does not run or repair the suite.
