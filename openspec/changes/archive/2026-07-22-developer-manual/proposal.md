## Why

Junior developers (and future agents) currently bounce between `docs/context.md`, `system.md`, `lld.md`, step prompts, and source stubs without a single map of **where code lives, why layers exist, and which file imports what**. With P0–P1 complete and P2 underway, now is the right time to add a living developer manual before the codebase grows harder to navigate.

## What Changes

- Create a **developer manual** (not end-user product docs) as the junior-friendly orientation guide for Wandr backend
- Use `docs/app/documentation.md` as the **entry index**, with focused pages under `docs/manual/` (layers, module map, import/call graph, “how to change X”, AI/LLM boundary, update cadence)
- Document **what exists today** (through P2.2: scaffold, DB/auth, geo geocoder + overpass) and explicitly mark **stubs vs real**
- Explain **why** each layer exists (Router → Service → Repository; `geo/`; `core/llm`; future `travel_engine` / planner) without duplicating AGENT.md or the full blueprint
- Add a **maintenance rule**: refresh the manual after each **full phase** (P0/P1/P2…) **or** every **4–5 validated steps**, whichever comes first; link from `docs/context.md` and optionally `.cursorrules`
- Non-goals: API reference auto-gen, OpenAPI dump, rewriting `system.md`/`lld.md`, documenting unbuilt planner/Qdrant features as if shipped

## Capabilities

### New Capabilities

- `developer-manual`: Living junior-oriented developer manual covering layers, module/file map, import connections, change-navigation guides, and update cadence

### Modified Capabilities

- (none)

## Impact

- **Docs:** `docs/app/documentation.md` (index), new `docs/manual/*.md`, pointer in `docs/context.md`, optional maintenance bullet in `.cursorrules`
- **Code/APIs:** none — documentation-only change
- **Deps:** none
- **AGENT.md:** no rule changes; manual links to AGENT.md for hard constraints
- **Audience:** human juniors + onboarding; agents still start with `docs/context.md` (manual is complementary, not a replacement)
