## Why

Backend has a definitive build bible (`docs/blueprint_final.md`) with principles, AGENT guardrails, resilience contracts, failure boundaries, and phased steps that each end in a runnable proof. The frontend only has `docs/FE_guide.md` — a solid stack + API contract — but not a phased, failure-first development blueprint. Before scaffolding the sibling Next.js repo, we need the same rigor for FE: tight principles, named fallbacks, no happy-path-only steps, system-design patterns, and agent guardrails — so Cursor (and humans) build `wandr-web` the way we built the API.

## What Changes

- Add `docs/blueprint_frontend.md` as the **single source of truth for frontend development** (mirror role of `docs/blueprint_final.md` for the planner/backend).
- Embed FE **Principles**, **AGENT.md guardrails** (for the sibling FE repo), **Resilience / UX failure contracts**, **Failure Boundary Summary**, **LLD pattern reference**, **package install order**, and a **phased step blueprint** (F0–Fn) where every step names pattern + failure boundary + proof command.
- Keep `docs/FE_guide.md` as the locked stack + live API integration contract; the new blueprint **consumes** it and must not fork endpoint/DTO truth.
- Document FE-specific product decisions discovered in guide review (e.g. day narrative vs durable `TripOut`, incomplete OAuth return) as explicit MVP rules + follow-ups — not silent omissions.
- Point `docs/context.md` at the FE blueprint (deployment/frontend notes only — no Progress-table churn).
- **Non-goals:** scaffolding the Next.js app; implementing FE screens; changing FastAPI routes; hosting/VPS FE SOP; replacing `FE_guide.md`.

## Capabilities

### New Capabilities

- `frontend-dev-blueprint`: Requirements for `docs/blueprint_frontend.md` — FE principles, AGENT guardrails, resilience/failure tables, phased F-steps with proofs, package order, and relationship to `FE_guide.md` / backend Option A.

### Modified Capabilities

- (none — documentation SSOT for a sibling FE repo; no backend requirement deltas in this change)

## Impact

- **Docs:** `docs/blueprint_frontend.md` (new); soft pointer from `docs/context.md`; `docs/FE_guide.md` stays canonical for stack/API (may get a one-line “see blueprint for phased build” cross-link).
- **OpenSpec:** `openspec/changes/frontend-blueprint/` planning artifacts.
- **Code:** none in this repo (no FE scaffold, no API changes). Implementation of the app happens later in the sibling FE repo following this blueprint.
- **Coupling:** Blueprint MUST stay aligned with live endpoints / schemas / SSE / GeoJSON as mirrored in `FE_guide.md`; when API DTOs change, update guide + any blueprint DTO references in the same PR.
- **AGENT.md conflict check:** Backend `AGENT.md` stays API-only. FE blueprint defines a **separate** FE `AGENT.md` content block for the sibling repo — do not merge FE rules into backend `AGENT.md`.
