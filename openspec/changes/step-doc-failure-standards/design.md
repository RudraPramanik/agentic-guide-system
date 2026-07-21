## Context

Wandr's blueprint (`docs/blueprint_final.md`) treats resilience as law: Resilience Contracts table, Failure Boundary Summary (~30 rows), AGENT.md non-negotiables, and 🚨 markers on every phase step. P1's `step1.md` already embeds failure conventions (lines 25–28) and per-step boundaries (OAuth 502, rate limit fail-open, session rollback).

**Gap:** P2–P7 have no `stepN.md` files. When they are written, authors need a single template so every step includes:
1. Cited failure boundary from blueprint
2. Implementation constraints (timeouts, retry, fallback)
3. At least one **verifiable failure proof** alongside the happy-path ✅

OpenSpec specs should mirror this with WHEN/THEN failure scenarios.

## Goals / Non-Goals

**Goals:**

- One reusable doc: `docs/steps/FAILURE_STANDARDS.md`
- Every future step prompt block includes a **Failure boundary** subsection
- Minimum failure-proof matrix by step category
- Playbook update in `docs/spec.md` so humans know when to add failure specs

**Non-Goals:**

- Duplicating the full Resilience Contracts table (link to blueprint instead)
- Full P2 step content
- Changing runtime code or AGENT.md rules

## Decisions

### D1 — Standalone `FAILURE_STANDARDS.md` vs inline-only

**Decision:** Create `docs/steps/FAILURE_STANDARDS.md` as the canonical reference; step files link to it in Prompt conventions.

**Rationale:** Avoids pasting 200 lines into every step file. step1.md keeps its one-line summary + link.

**Alternative rejected:** Embed full standards only in blueprint — too far from Cursor prompts agents actually read.

### D2 — Per-step prompt structure (mandatory blocks)

Every step prompt in `stepN.md` MUST contain:

```markdown
─── FAILURE BOUNDARY ───
- Blueprint ref: [Resilience Contracts row OR Failure Boundary Summary row]
- On failure: [typed error / fallback / degrade behavior]
- Must NOT: [e.g. raise 500, leak stack trace, block user on limiter bug]

─── VALIDATION ───
✅ Happy path: [command + expected output]
✅ Failure path: [command or mock + expected status/behavior]
```

### D3 — Minimum failure proofs by category

| Step type | Min failure proofs | Example |
|-----------|-------------------|---------|
| External gateway (`geo/`, `llm/`) | 2 | network down → fallback; timeout after retries → named error |
| HTTP API router | 1 | auth fail → 401/403; validation → 422 not 500 |
| DB migration | 1 | re-run idempotent OR downgrade safe |
| Middleware | 1 | internal error → fail open (rate limit) or fail closed with typed error |
| Pure Python (`travel_engine/`) | 0 external; 1 bad input | invalid itinerary → ValidationResult errors |
| Agent / tool | 2 | wrong-phase tool → precondition_failed; ceiling → abort_triggered |
| Batch script | 1 | single record fail → log + continue |

### D4 — OpenSpec alignment

**Decision:** Every OpenSpec change that adds external I/O MUST include ≥1 `#### Scenario:` failure case in its delta spec, citing the blueprint fallback.

**Rationale:** Specs become test contracts; pytest can implement scenarios later.

### D5 — step2.md skeleton only

**Decision:** This change adds `step2.md` **header + conventions + empty step outline with failure placeholders** — not full P2 prompts.

**Rationale:** Full P2 authoring is a separate `/opsx-propose p2-geo-foundation` slice.

### D6 — Backfill scope for P0/P1

**Decision:** Update only the shared **Prompt conventions** section in step0.md and step1.md to link `FAILURE_STANDARDS.md`. Do not rewrite all 13 P1 prompt bodies.

**Rationale:** P1 steps already have embedded boundaries; full retrofill is low ROI.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Template becomes boilerplate noise | Keep FAILURE BOUNDARY to 3–5 bullets; link blueprint for details |
| Failure proofs hard to automate | Prefer unit tests with mocks over "kill network" for CI; reserve manual chaos for P6 checklist |
| Doc drift from blueprint | Template requires explicit blueprint row citation per step |
| Agents skip failure validation | tasks.md final item: "both ✅ checks pass before next step" |

## Migration Plan

1. Add `docs/steps/FAILURE_STANDARDS.md`
2. Patch `docs/spec.md` § workflow
3. Patch Prompt conventions in step0.md + step1.md
4. Add step2.md skeleton with failure placeholders per P2 blueprint step
5. Future phases: author stepN.md using template before `/opsx-propose` for that phase

## Open Questions

- Should failure proofs be **required in CI** from P2 onward (pytest marker `@pytest.mark.failure`)? → defer to P2 propose change.
- Windows-specific failure commands: document mock-based proofs as primary, network-kill as optional manual check.
