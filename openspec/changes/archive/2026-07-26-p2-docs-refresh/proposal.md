## Why

P2 code and `docs/context.md` / `docs/steps/step2.md` are closed out through 2.9–2.10, but the junior developer manual and P2 study guide still describe the world as of **P2.8** (pytest/smoke “not built yet”, geo/destinations/places still “stubs”). The locked cadence in `docs/manual/06-maintenance.md` and `.cursorrules` requires a manual refresh when a full phase finishes — that trigger just fired and was not applied.

## What Changes

- Refresh `docs/app/documentation.md` + `docs/manual/*` to **Through step: P2.10** (phase-complete cadence).
- Sync module map / wiring / recipes with `context.md`: real P2 pytest packages, `scripts/test_p2_smoke.py`, `seed_destination_into`, formula-true readiness floors (`place_count >= 100` preferred for limited-band; `50` is volume-only).
- Update `docs/app/p2guide.md` so it no longer claims P2 modules are stubs or “You are here” as incomplete; mark P2 as done and point next work at P3.1.
- Light-touch `docs/app/system.md` / `docs/app/lld.md` only where a factual drift vs post-P2 reality exists (no architecture rewrite).
- **Non-goals:** no application code, no new OpenSpec backfill of the whole blueprint, no rewrite of `step2.md` / `context.md` (already current), no traveler/product docs.

## Capabilities

### New Capabilities
- `p2-study-guide`: Keep `docs/app/p2guide.md` aligned with completed P2 (real modules, live endpoints, verification artifacts) without turning it into a step prompt.

### Modified Capabilities
- `developer-manual`: Phase-complete refresh — index marker through P2.10, module map / wiring / recipes / maintenance log match `context.md` after 2.9–2.10.

## Impact

- Docs only: `docs/app/documentation.md`, `docs/manual/01–06`, `docs/app/p2guide.md`, optionally small corrections in `docs/app/system.md` / `docs/app/lld.md`.
- No runtime APIs, migrations, or package changes.
- Agents reading the manual after this change will correctly treat geo/destinations/places as real and P3.1 as next.
