## Context

Wandr already has agent-oriented docs (`docs/context.md`), architecture (`docs/app/system.md`), patterns (`docs/app/lld.md`), OpenSpec playbook (`docs/spec.md`), and step prompts. `docs/app/documentation.md` is empty. Juniors need a **narrative map**: layers, why they exist, file↔file connections, and “I want to change X → start here,” without reading the whole blueprint. Scope of first write-up: everything real through **P2.2** (per `docs/context.md`); stubs called out explicitly.

## Goals / Non-Goals

**Goals:**
- Junior-readable developer manual with clear entry point and deep links
- Layer explanation (HTTP → service → repo → DB; geo gateways; LLM gateway; future AI planner boundary)
- Module/file map + import/call relationships for implemented code
- “How to change…” recipes for common tasks (add endpoint, add env var, touch geo, add migration)
- Documented update cadence: after each **full phase** or every **4–5 validated steps**
- Wire pointers from `docs/context.md` (and a short maintenance note in `.cursorrules`)

**Non-Goals:**
- End-user / traveler product documentation
- Duplicating AGENT.md, full blueprint, or OpenSpec playbook verbatim
- Auto-generating docs from AST (manual curated tables for v1)
- Documenting stub modules as if they had public APIs
- Changing application code, APIs, or OpenSpec schemas beyond doc pointers

## Decisions

### D1 — Multi-page manual under `docs/manual/`, index at `docs/app/documentation.md`
- **Why:** One huge file becomes unmaintainable; juniors need a TOC. The empty `documentation.md` is the natural hub the user already opened.
- **Alt rejected:** Single mega-`documentation.md` only — hard to update incrementally.
- **Structure (v1):**
  - `docs/app/documentation.md` — purpose, read order, TOC, “last refreshed through step X”
  - `docs/manual/01-orientation.md` — what Wandr is, how docs layers relate (context vs manual vs system vs steps)
  - `docs/manual/02-layers.md` — request path, why each layer, AI/LLM vs deterministic code
  - `docs/manual/03-module-map.md` — package → responsibility → key files (real vs stub)
  - `docs/manual/04-imports-and-wiring.md` — who imports whom (auth, geo, core, main)
  - `docs/manual/05-how-to-change.md` — recipes for common feature work
  - `docs/manual/06-maintenance.md` — when/how to refresh the manual

### D2 — Truth sources and non-duplication
| Topic | Source of truth | Manual role |
|-------|-----------------|-------------|
| What’s done / stubs | `docs/context.md` | Snapshot + link; never invent “done” |
| Hard coding rules | `AGENT.md` | Short reminders + link |
| Architecture essays | `system.md` / `lld.md` | Summarize + link |
| Step instructions | `docs/steps/` | Do not copy; link by phase |
| Behavior contracts | `openspec/specs/` | Mention; do not restate every SHALL |

### D3 — Update cadence (locked)
Refresh the manual when **either**:
1. A **full phase** closes (e.g. all of P1, all of P2), **or**
2. **4–5 consecutive validated steps** land since `Last refreshed` on the index

Whichever comes first. Agents completing a step still update `context.md` every time; they only touch the manual when the cadence rule fires (or when explicitly asked).

### D4 — Content depth for v1 (through P2.2)
Must cover with concrete file paths:
- App factory / lifespan / middleware (`src/main.py`, logging + rate limit)
- Config (`src/config.py` + `get_settings()`)
- Core: DB session/base/repo, JWT/permissions, responses, exceptions, LLM client, pagination
- Auth package (router → service → repository)
- Geo: `schemas`, `geocoder`, `overpass` (real); `osrm` stub
- Migrations / Alembic overview
- Scripts and tests entry points
- Explicit “not built yet”: destinations/places services, planner, search, travel_engine logic

### D5 — Import/wiring diagrams as mermaid + tables
- Mermaid for request flow and auth/geo call chains
- Tables for “File A imports File B for reason Z”
- Prefer accuracy over completeness; mark stubs

### D6 — Maintenance hooks
- Index header: `Last refreshed: YYYY-MM-DD · Through step: P2.2`
- `docs/context.md`: one link under deep refs / quick ref
- `.cursorrules` docs maintenance: add bullet for manual cadence (do not paste full AGENT.md)

## Risks / Trade-offs

- [Docs drift from code] → Cadence rule + “verify against context.md Implemented modules before editing”; prefer links over copied APIs
- [Overlap with system.md / lld.md] → Manual is navigation + why-for-juniors; deep design stays in system/lld
- [Over-documenting stubs] → Hard rule: stub packages get one row “placeholder — no public API yet”
- [Agents ignore cadence and rewrite every step] → Explicit “do not update manual every step” in maintenance page + cursorrules

## Migration Plan

1. Create `docs/manual/` pages + fill `docs/app/documentation.md` index
2. Add context.md + `.cursorrules` pointers
3. Sanity-check: every “real” module listed in context appears; every stub marked
4. Rollback: delete `docs/manual/` and revert index/pointers — no code impact

## Open Questions

- None blocking. (Product/user docs deferred; name is “developer manual” not “user guide.”)
