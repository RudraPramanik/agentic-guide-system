## Why

P7 (7.0–7.6) and production packaging are recorded complete in `docs/context.md` (Next → operator VPS deploy via `docs/steps/blueprint_production.md`), but the developer manual is still frozen at **Through step: P6.5** and still describes trip edit/replan HTTP as unbuilt. That violates the locked cadence in `docs/manual/06-maintenance.md` (refresh on phase end) and will mislead agents and juniors. `docs/app/system.md` and `docs/app/lld.md` still carry “edit/replan HTTP later (P7)” framing and Build Progress “through P6.5” that contradict post-P7 reality.

## What Changes

- Refresh `docs/app/documentation.md` + `docs/manual/*` to **Through step: P7.6** (or the highest validated P7 step in `context.md` at apply time — expected P7.6 / post-P7).
- Sync module map / layers / wiring / recipes with `context.md`: base prefs persist (7.0), shared `populate_leg_polylines` (7.1), TripService day surgery + preserve-order schedule + TripEditEvent UoW (7.2), trips edit HTTP (4 routes) + `rate_limit_trip_edit` (7.3), edit/replan pytest (7.4), evaluation `mark_trip_edited` flag polish (7.5), P7 smoke + context close-out (7.6). Also note production packaging / hosted embeddings / deploy SOP where the manual snapshot and architecture docs currently imply MiniLM-only or “P7 next”.
- Keep stubs explicit for what `context.md` still marks stub: evaluation HTTP, `auth/dependencies.py`, clarification-path evaluation note where still deferred. **Do not** keep calling P7 edit/replan HTTP a stub.
- Light-touch `docs/app/system.md` / `docs/app/lld.md` only where factual drift vs post-P7 reality exists (no architecture rewrite) — e.g. trips row, Build Progress, pattern catalog for edit UoW / preserve-order / user-keyed trip-edit rate limit / shared polyline helper.
- **Non-goals:** no application code; no rewrite of blueprint / `AGENT.md` / step prompts; no inventing evaluation HTTP APIs; no traveler/product docs; no full essay rewrite of system/lld; no mandatory `p2guide.md` or `FE_guide.md` rewrite unless a concrete contradiction with post-P7 “next” framing is found during apply; no implementing `docs/next_version.md` roadmap items.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `developer-manual`: Phase-catch-up refresh — index marker through P7 (expected P7.6 / post-P7); module map / layers / wiring / recipes / maintenance log match `context.md` after P7 + production packaging notes; stubs only where context still says stub (evaluation HTTP, `auth/dependencies.py`, etc.). Architecture docs (`system.md` / `lld.md`) light-touch for post-P7 factual drift.

## Impact

- Docs only: `docs/app/documentation.md`, `docs/manual/01–06`, opportunistic corrections in `docs/app/system.md` / `docs/app/lld.md`. `docs/context.md` already reflects P7 complete — touch only if a checklist mismatch is found (docs-only; no inventing modules).
- No runtime APIs, migrations, or package changes.
- Agents reading the manual after this change will correctly treat trip edit/replan HTTP, shared polyline helper, and P7 verification as real, and operator VPS deploy as next.
