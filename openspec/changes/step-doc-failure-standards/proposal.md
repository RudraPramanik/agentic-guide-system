## Why

`docs/blueprint_final.md` defines production-grade failure boundaries (Resilience Contracts table, Failure Boundary Summary, per-step 🚨 markers), but only P0/P1 have expanded step prompts (`step0.md`, `step1.md`). P2–P7 step docs do not exist yet. Without a repeatable template, future step authors and Cursor agents will implement happy paths first and leave failure proofs inconsistent — undermining the blueprint's strongest property.

## What Changes

- Add a **canonical failure-standards template** for all `docs/steps/step*.md` files.
- Extend **Prompt conventions** in existing step docs to reference the template explicitly.
- Update **`docs/spec.md`** playbook with a "Failure proofs required" section linking blueprint tables → step validation → OpenSpec scenarios.
- Provide a **skeleton `docs/steps/step2.md` header** (P2 geo) pre-wired with failure sections — full P2 prompts are a separate change.
- Define minimum failure-proof counts per step type (gateway, API, agent, DB migration).

**Non-goals:**

- Rewriting `docs/blueprint_final.md`.
- Implementing P2+ code or full step2.md content.
- Adding ops runbooks, SLOs, or alerting (post-P6 concern).
- Retrofitting every completed P0/P1 step prompt with new failure blocks (only update the shared conventions section).

## Capabilities

### New Capabilities

- `step-doc-failure-standards`: Requirements for how every build step doc MUST document failure boundaries, cite Resilience Contracts, and include verifiable failure proofs.

### Modified Capabilities

- _(none — no runtime behavior change; documentation and process only)_

## Impact

| Area | Impact |
|------|--------|
| `docs/steps/` | New `FAILURE_STANDARDS.md`; updated conventions in step0/step1; step2 skeleton header |
| `docs/spec.md` | New subsection under build workflow |
| `openspec/` | Future change specs MUST include ≥1 failure scenario per external I/O capability |
| Runtime code | None until P2+ steps are authored using the template |
