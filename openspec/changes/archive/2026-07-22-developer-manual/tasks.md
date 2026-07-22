## 1. Manual structure

- [x] 1.1 Create `docs/manual/` and write `docs/app/documentation.md` index (purpose, Last refreshed / through step **P2.2**, read order, TOC linking all manual pages)
- [x] 1.2 Write `docs/manual/01-orientation.md` — how context / AGENT / system / lld / steps / OpenSpec / this manual relate; who reads what

## 2. Layers and module map

- [x] 2.1 Write `docs/manual/02-layers.md` — request path, Router→Service→Repository, geo gateways, `core/llm` AI boundary, deterministic vs LLM (link AGENT.md)
- [x] 2.2 Write `docs/manual/03-module-map.md` — packages/files through P2.2 from `docs/context.md` Implemented modules; stubs called out explicitly

## 3. Wiring and recipes

- [x] 3.1 Write `docs/manual/04-imports-and-wiring.md` — mermaid + tables for main/auth/geo/core import and call chains
- [x] 3.2 Write `docs/manual/05-how-to-change.md` — recipes: env setting, new endpoint, geo call, migration, run scripts/tests

## 4. Maintenance hooks

- [x] 4.1 Write `docs/manual/06-maintenance.md` — cadence (full phase **or** every 4–5 steps), what to update, what not to duplicate
- [x] 4.2 Add developer-manual link + cadence note to `docs/context.md`; add maintenance bullet to `.cursorrules`
- [x] 4.3 Sanity-check: every Implemented module in context appears as real; every listed stub is marked stub-only
