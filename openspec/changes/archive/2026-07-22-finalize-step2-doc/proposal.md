## Why

`docs/steps/step2.md` (v1) is the P2 Cursor prompt doc, but a hardened review (`docs/steps/suggestedp2.md` v2) found correctness bugs and ambiguous decisions that would ship into Agent mode as written. We need a single canonical `step2.md` before any P2 implementation starts — agents must not implement from a known-broken prompt.

## What Changes

- Replace `docs/steps/step2.md` with the hardened v2 content from `docs/steps/suggestedp2.md` (canonical build order, locked decisions, failure proofs).
- Remove or archive `docs/steps/suggestedp2.md` after promote (keep one source of truth).
- Point `docs/context.md` Next-step guidance at the finalized `step2.md` if needed (P2.1 still next; no code).
- **No application code** in this change — documentation finalize only.

Key v2 fixes adopted:

1. Async geocode cache: no `@functools.lru_cache` on `async def` (manual dict + lock)
2. Atomic `ON CONFLICT` upserts for `osm_id` / `osm_place_id` (no check-then-insert races)
3. Radius search locked to PostGIS `geography` (meters), not geometry degrees
4. Path-specific rate limit on `GET /destinations/search` (20/min) via step 2.6c′
5. Mandatory destination existence check on places list (404, not empty page)
6. Canonical step order: `2.6a/b` before `2.4`; remove “amendment” patch notes
7. Expanded pytest (cache hit, seed partial failure, geography unit regression)
8. Runnable validation scripts (remove broken `divmod` snippet)

## Capabilities

### New Capabilities

- `p2-step-doc`: Canonical P2 Cursor prompt document standards — locked geo/readiness decisions, concurrency-safe upsert rules, failure-boundary proofs, and single build order for Agent mode.

### Modified Capabilities

- *(none — no runtime behavior change in this change; geo-foundation specs remain in `wandr-backend-roadmap` until P2 code ships)*

## Impact

- **Files:** `docs/steps/step2.md`, `docs/steps/suggestedp2.md` (remove after promote), optionally a one-line pointer in `docs/context.md`
- **Agents:** Future `/opsx:apply` / Agent-mode P2 steps use finalized prompts only
- **Code/APIs:** None in this change
- **AGENT.md:** Geo-gateway, layering, resilience contracts unchanged — v2 strengthens them in the step doc
