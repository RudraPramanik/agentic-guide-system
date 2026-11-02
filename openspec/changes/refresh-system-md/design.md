## Context

See `proposal.md` for motivation. `docs/context.md` (Last updated 2026-08-30) is the factual checkpoint: P7 done, V0–V6.1 done, next = first VPS deploy. `docs/app/system.md` still mixes durable architecture with a P0 step-by-step diary and outdated “not yet” claims. Junior manual (`documentation.md` / `docs/manual/`) was already refreshed through P7 + V6.1; this change does not re-open that cadence. No runtime code changes.

## Goals / Non-Goals

**Goals:**
- Rewrite `docs/app/system.md` into a readable architecture deep reference that matches context.
- Keep AGENT.md / blueprint / FE_guide as linked SSOT for rules, build steps, and API contract detail.
- Make false claims impossible to miss in review (grep-level: “No domain routers”, “No X-Request-ID yet”, Redis-off-only).

**Non-Goals:**
- Rewriting `docs/manual/*` or `documentation.md`.
- Full `lld.md` rewrite (optional one-line honesty only).
- Updating `docs/context.md` unless a contradiction with the new `system.md` is found (prefer fixing system.md to match context).
- Documenting every Live endpoints row verbatim (summary + pointer to context / FE_guide is enough).

## Decisions

### D1 — Replace diary sections with durable architecture outline
**Choice:** Keep a short product intro + layering diagram, then domain map, request path, planner loop, search/routing, trips, observability, local infra, stubs, agent constraints. Drop per-step 0.4–1.2 implementation essays and the P0 verification checklist (or shrink to a one-line “historical P0 checks → see archive / context”).
**Why:** Context already owns step progress; system.md should answer “how is the system shaped?” not “what did step 0.10 do?”.
**Alternatives:** Patch only status rows (rejected — leaves structure misleading); merge system.md into context (rejected — context must stay lean).

### D2 — Fact source for the rewrite
**Choice:** Treat `docs/context.md` as authoritative for what is real vs stub; use `docs/FE_guide.md` / Live endpoints only for high-level surface mention; do not invent modules.
**Why:** Matches `.cursorrules` and AGENT session order.
**Alternatives:** Re-derive from source tree alone (risk inventing APIs); copy blueprint wholesale (too large, includes unbuilt intent).

### D3 — Local infra table
**Choice:** Document Compose services as Postgres 5433, Qdrant 6335/6336, Redis host 6380, API 8000; note empty host `REDIS_URL` → in-memory for pytest/host uvicorn vs Compose API injecting Redis.
**Why:** Current system.md incorrectly says Redis is feature-flagged off in a way that implies Compose has no Redis.
**Alternatives:** Omit Redis entirely (rejected — agents misconfigure multi-worker assumptions).

### D4 — Build Progress section
**Choice:** Replace the long early-step table with a one-line phase rollup (“P0–P7 + V0–V6.1 ✅; V6.2/V6.3 deferred; next = VPS deploy”) and link to `docs/context.md`.
**Why:** Spec forbids Progress-table clone; reduces drift.
**Alternatives:** Keep expanding the table (rejected — duplicates context).

### D5 — Package versions
**Choice:** Remove pinned version callouts from system.md; point to `requirements.txt`.
**Why:** Versions drift; prior system.md already had stale pins risk.
**Alternatives:** Keep “illustrative” pins (rejected — become false facts).

### D6 — lld.md
**Choice:** Only touch `lld.md` if a quick read finds a claim that still contradicts context after system.md refresh; otherwise leave it.
**Why:** Proposal non-goal is no full lld rewrite; prior catch-up already light-touched it.

## Risks / Trade-offs

- **[Risk] Rewrite is large and reviewers skim → Mitigation:** Keep sections short; lead with corrected claims; tasks include a contradiction checklist against context.
- **[Risk] Over-documenting Live endpoints creates a third SSOT → Mitigation:** Summary bullets + link to context Live endpoints / FE_guide.
- **[Risk] Stale OpenSpec project context still says “Current phase: P1” → Mitigation:** Ignore that CLI boilerplate; use `docs/context.md` only.
- **[Trade-off] Losing P0 step essays → Acceptable:** historical build detail lives in steps/archive; architecture doc should not be a changelog.

## Migration Plan

1. Write the new `docs/app/system.md` content in-place (single file replace/rewrite).
2. Spot-check against context stubs + Live endpoints.
3. Optional `lld.md` one-liner if needed.
4. No deploy / no rollback beyond git revert of the doc file.

## Open Questions

None — scope is docs-only; factual baseline is `docs/context.md`.
