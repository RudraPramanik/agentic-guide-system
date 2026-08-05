## Why

P5 closed and P6 (6.0–6.5) is recorded complete in `docs/context.md` (Next → P7.1), but the developer manual is still frozen at **Through step: P5.11** and still describes trips HTTP, `POST /planner/generate`, and Redis/planner cache as unbuilt. That violates the locked cadence in `docs/manual/06-maintenance.md` (refresh on phase end) and will mislead agents starting P7. `system.md` / `lld.md` still carry “trips HTTP later”, “planner HTTP generate P6”, and “planner cache later” framing that contradicts post-P6 reality.

## What Changes

- Refresh `docs/app/documentation.md` + `docs/manual/*` to **Through step: P6.5** (or the highest validated P6 step in `context.md` at apply time — expected P6.5).
- Sync module map / layers / wiring / recipes with `context.md`: route polylines (6.0), trips repo/service + HTTP CRUD/GeoJSON/claim (6.1–6.3), planner SSE `/generate` + floor/persist (6.2), `CacheBackend` + Redis/InMemory rate limiter + planner MVP cache (6.4), P6 pytest + `scripts/test_p6_smoke.py` (6.5). Also catch up any still-stale P5.12–5.14 framing (PlannerService bridge, tool-loop tests, agent smoke) if the index never moved past P5.11.
- Keep stubs explicit for what `context.md` still marks stub after P6: P7 trip edit/replan HTTP, evaluation HTTP, `auth/dependencies.py`, clarification-path evaluation note where still deferred.
- Light-touch `docs/app/system.md` / `docs/app/lld.md` only where factual drift vs post-P6 reality exists (no architecture rewrite) — e.g. trips/planner rows, Cache-Aside / rate-limiter / Strategy status cells.
- **Non-goals:** no application code; no rewrite of blueprint / `AGENT.md` / step prompts; no inventing P7 edit/replan APIs; no traveler/product docs; no full essay rewrite of system/lld; no mandatory `p2guide.md` rewrite unless a concrete contradiction with post-P6 “next” framing is found during apply.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `developer-manual`: Phase-catch-up refresh — index marker through P6 (expected P6.5); module map / layers / wiring / recipes / maintenance log match `context.md` after P6; stubs only where context still says stub (P7 edit/replan, evaluation HTTP, `auth/dependencies.py`, etc.). Architecture docs light-touch for post-P6 factual drift.

## Impact

- Docs only: `docs/app/documentation.md`, `docs/manual/01–06`, opportunistic corrections in `docs/app/system.md` / `docs/app/lld.md`. `docs/context.md` already reflects P6 complete — touch only if a checklist mismatch is found (docs-only; no inventing modules).
- No runtime APIs, migrations, or package changes.
- Agents reading the manual after this change will correctly treat planner SSE generate, trips HTTP, and Redis/in-memory cache backends as real, and P7.1 as next.
