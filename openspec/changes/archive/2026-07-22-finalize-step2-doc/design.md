## Context

P1 is complete. `docs/steps/step2.md` was drafted as the P2 Agent-mode prompt pack (13 prompts expanding blueprint P2). A review produced `docs/steps/suggestedp2.md` (v2 — hardened) that fixes correctness bugs and locks ambiguous decisions. This change promotes v2 to the single canonical `step2.md` before any P2 code work.

Constraints: docs-only; AGENT.md geo/layering rules unchanged; no runtime packages.

## Goals / Non-Goals

**Goals:**

- One canonical P2 step document agents paste from
- Preserve all v2 Fix Log items (async cache, atomic upserts, geography cast, search rate limit, mandatory dest check, canonical order, expanded tests)
- Keep failure-boundary + failure-path validation standards from step-doc-failure-standards

**Non-Goals:**

- Implementing any P2 application code
- Rewriting `openspec/changes/wandr-backend-roadmap` geo-foundation specs in this change
- Changing blueprint_final.md readiness formula (v2 already documents P2 `tier=limited` amendment)

## Decisions

### D1 — Promote suggestedp2 wholesale as step2.md

**Decision:** Copy `docs/steps/suggestedp2.md` content over `docs/steps/step2.md`, then delete `suggestedp2.md`.

**Alternatives:** (a) Diff-merge only the Fix Log into v1 — higher risk of missing a locked decision; (b) Keep both files — agents will pick the wrong one.

**Rationale:** v2 is a complete supersession, not a patch set.

### D2 — Canonical build order is the only order

**Decision:** Document order only once:

`2.1 → 2.2 → 2.3 → 2.6a → 2.6b → 2.4 → 2.5 → 2.6c → 2.6c′ → 2.7a → 2.7b → 2.8 → 2.9 → 2.10`

**Rationale:** Seed (2.4) needs DestinationRepository atomic upsert from 2.6b; numbering-vs-order confusion in v1 caused the “amendment” footnote.

### D3 — Accept known residual limitations in the doc (do not block finalize)

| Residual | Treatment |
|----------|-----------|
| Geocoder cache stampede (miss releases lock before fetch) | Documented as per-process; Nominatim throttle serializes outbound calls; Redis upgrade at P6 |
| Same-session “race” upsert validation ≠ true multi-session concurrency | Still proves ON CONFLICT idempotency; true concurrency is Postgres-level |
| 2.6c wires readiness route before 2.8 implements `get_readiness` | Explicit stub note in v2 — acceptable for linear prompts |

### D4 — No context.md Progress flip until P2 code ships

**Decision:** After promote, `docs/context.md` may note “P2 prompts finalized in step2.md (v2)” but Progress table stays at P2.1 pending — do not mark geo modules implemented.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Agents still open stale step2 from chat history | Delete suggestedp2; header on step2 says “v2 — hardened” + Fix Log |
| Blueprint still says readiness `tier=ready` after seed | step2 P2 note + ship criteria use `limited`; design decision locked |
| Unicode prime in `2.6c′` breaks some tooling | Keep as in v2 (readable); if Windows tooling fails, alias to `2.6d` in a follow-up |

## Migration Plan

1. Overwrite `docs/steps/step2.md` with contents of `suggestedp2.md`
2. Delete `docs/steps/suggestedp2.md`
3. Optional one-liner in `docs/context.md` under Current state / Next step
4. Archive this OpenSpec change after apply
5. Next implementation change: `/opsx:propose step-2-1-geocoder` grounded in finalized step2.md

## Open Questions

None blocking finalize. Optional later: rename `2.6c′` → `2.6d` for ASCII-only IDs.
