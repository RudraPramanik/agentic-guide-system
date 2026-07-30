## Why

P3 is complete (enrichment + Qdrant + readiness). `src/travel_engine/` and planner routing/tools remain stubs, and `docs/steps/step4.md` is empty. `docs/blueprint_final.md` v6.1 locks P4 vocabulary and algorithms at the product level, but agents still need a step2/step3-style Cursor build prompt — sub-steps, failure boundaries, ✅ validation, pytest, and real smoke proof — before coding. Without that contract, implementers re-invent APIs, conflate structural `Place.category` with interest `enriched_tags`, or leak `geo/` into the pure engine.

## What Changes

- Author **`docs/steps/step4.md`** as the hardened P4 Cursor prompt (same shape as `step2.md` / `step3.md`): prerequisites, architecture diagram, locked decisions, ordered sub-steps **4.0–4.8** (+ pytest **4.9** + smoke **4.10**), each with TASK / FAILURE BOUNDARY / ✅ validation.
- Align this change’s design/specs/tasks to **`docs/blueprint_final.md` v6.1** (Planner SoT). Former pointer-only `docs/blueprint.md` is not a second source of truth.
- Lock abstractions and fallbacks in the prompt: `RoutingProvider` DI, corrected `travel_rules`, sum scoring, brute-force route order, `dropped_stops`, wall-clock schedules, chain-of-checks validator, `OsrmRoutingProvider` + thin `execute_tool` stub, CORS.
- **Supersede doc intent** of the existing in-progress `p4-travel-engine` change for “author step4.md”; after this prompt lands and is applied, prefer implement-from-`step4.md` (archive or abandon stale tasks that still cite pre-v6.1 `blueprint.md` language).
- **Non-goals for this design change’s apply:** no production travel_engine code until a follow-on apply from the prompt (or a dedicated implementation change). This change’s primary deliverable is the prompt + OpenSpec alignment.

## Capabilities

### New Capabilities

- `p4-travel-engine-layer`: Contract for the pure-Python travel intelligence layer and P4 adjacency — protocols/rules, place selection, day allocation, route optimization with drop-retry, schedule building, trip validation, planner `OsrmRoutingProvider` + tool envelope stub, CORS middleware, unit/smoke verification — as specified in the hardened `docs/steps/step4.md` prompt.

### Modified Capabilities

<!-- Intentionally empty: no archived main-spec requirement deltas; this change authors the build prompt + delta specs under the change. -->

## Impact

- **Docs:** `docs/steps/step4.md` becomes the sole P4 implementation prompt (agents paste sub-steps in order). Blueprint remains architecture SoT, not the Cursor prompt.
- **Code (once implemented from the prompt):** `src/travel_engine/*` (today stubs), `src/planner/routing_provider.py`, thin `src/planner/tools/` envelope, `src/config.py` + `src/main.py` for CORS.
- **AGENT.md:** travel_engine stays pure (no LLM/network/DB); routing injected via `RoutingProvider`; geo only via `src/geo/` outside the engine.
- **Tests:** FakeRoutingProvider unit tests (no network); import guards; optional live OSRM smoke; pytest expands beyond current 92.
- **Process:** propose → apply (write step4.md) → archive this design change; then implement P4 from the prompt (batched OpenSpec applies per cluster of sub-steps, not one ceremony per micro-step).
- **Non-goals:** LangGraph, full tool registry, SSE, trip CRUD, Redis, SameSite code change (document Option A only), P5/P6 behavior beyond shapes P4 must emit (`dropped_stops`, explain strings).
