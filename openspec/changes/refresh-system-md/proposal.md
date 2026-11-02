## Why

`docs/app/system.md` is the named architecture deep reference, but it still reads like an early-P0/P1 build diary: it claims domain routers are unregistered, omits `X-Request-ID`, understates Redis in Compose, and rolls up progress only through a vague “1.3+ / through P6.5” line. Agents and humans who open it get a false picture of the post-P7 / v7 (V0–V6.1) system. Prior docs syncs only allowed light-touch status fixes; that left the document structurally stale.

## What Changes

- Refresh `docs/app/system.md` into a current architecture overview aligned with `docs/context.md` (P7 complete + V0–V6.1 done; next = first VPS deploy).
- Correct false local-dev claims (Compose Redis, registered routers, request logging, live endpoint surface at a summary level).
- Replace step-diary / “not yet” framing with durable architecture sections (layers, domains, planner loop, search, routing backends, trips/edit, observability, stubs).
- Keep package pin lists out of `system.md` (versions live in `requirements.txt`); avoid duplicating the full `context.md` progress table.
- **Non-goals:** no application code, no OpenAPI/runtime behavior changes, no full rewrite of `docs/app/documentation.md` / `docs/manual/`, no full rewrite of `docs/app/lld.md` unless a single contradictory claim must be fixed for honesty, no inventing evaluation HTTP or other stubs.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `developer-manual`: Replace the “architecture docs light-touch only” bar for `docs/app/system.md` with a requirement that `system.md` MUST be a current architecture deep reference consistent with post-P7 / V6.1 `docs/context.md` (structure + facts), not merely patched status rows.

## Impact

- **Docs:** `docs/app/system.md` (primary); optional one-line honesty fix in `docs/app/lld.md` only if it still contradicts context after the refresh.
- **Specs:** `openspec/specs/developer-manual` (delta under this change).
- **Code / APIs / deps:** none.
- **AGENT.md:** unchanged; `system.md` continues to point at it for hard rules.
