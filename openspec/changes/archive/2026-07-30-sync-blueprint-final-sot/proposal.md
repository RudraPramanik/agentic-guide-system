## Why

`docs/blueprint_final.md` is the intended single source of truth for the Planner, but a P4 pre-flight review (`docs/blueprint.md`) found correctness bugs and underspecified locks that never landed in the master doc. Agents following `blueprint_final.md` alone would ship wrong `travel_rules`, incomplete P5/P6 contracts, and silent doc drift. Fold the addendum into `blueprint_final.md` now — before P4 implementation — so one document remains authoritative.

## What Changes

- **Bump / annotate** `docs/blueprint_final.md` to absorb all LOCKED items from `docs/blueprint.md` (Sections A–F), so the master blueprint matches what P4+ will build.
- **Fix** the `travel_rules.py` draft: structural vs interest vocabulary split; complete P2 category durations; remove `sunrise_point`; correct `CATEGORY_WEIGHTS` coverage; document sum scoring and `.get(..., DEFAULT)`.
- **Specify** route_optimizer: brute-force permutation ordering; `dropped_stops` on drop-retry output.
- **Add** missing cross-cutting design: CORS + cookie SameSite Option A; ToolContext vs LangGraph state; DB session lifecycle preference; SSE producer/consumer + disconnect cancel; absolute readiness floor; cache key with base lat/lng; guest trip ownership rule; explain_selection → tool_trace; agent nudge + `tool_choice=required` mechanics.
- **Correct** Package Install Order (pytest at P1, not 7.3).
- **Update** P4–P6 step bullets so step prompts inherit the locks (not only design sections).
- **Clarify SoT hierarchy:** `blueprint_final.md` = planner master; `docs/blueprint.md` becomes a short pointer / changelog that the addendum was merged (or archived note) — avoid two competing long docs.
- **Align** open change `p4-travel-engine` docs to cite updated `blueprint_final.md` (remove “superseded by addendum” conflict wording).
- **Non-goals:** no application code; no implementing P4–P6; no rewriting `docs/app/system.md` / LLD wholesale.

## Capabilities

### New Capabilities

- `planner-blueprint-sot`: Requirements for keeping `docs/blueprint_final.md` as the authoritative Planner blueprint, including vocabulary, routing, resilience, and P4–P6 locked behaviors merged from the pre-flight addendum.

### Modified Capabilities

<!-- Intentionally empty: documentation SoT change; no archived runtime capability requirements change in this PR. -->

## Impact

- **Docs:** `docs/blueprint_final.md` (primary), `docs/blueprint.md` (demote to merged/pointer), optionally one-line pointer in `docs/context.md`.
- **Downstream:** `openspec/changes/p4-travel-engine` proposal/design cross-refs; future `docs/steps/step4.md` (and later P5/P6 step docs) must match the updated master.
- **Code:** none in this change.
- **AGENT.md:** no text change required; blueprint text will reinforce existing rules (travel_engine purity, resilience, tool registry).
