## 1. Create failure standards doc

- [ ] 1.1 Create `docs/steps/FAILURE_STANDARDS.md` with: purpose, mandatory prompt blocks (FAILURE BOUNDARY + dual ✅ validation), minimum proofs matrix, blueprint citation rules, OpenSpec alignment, examples from step1 (OAuth 502, rate limit fail-open, JWT never 422)
- [ ] 1.2 Include copy-paste template snippet for new step prompts

## 2. Update developer playbook

- [ ] 2.1 Add "Failure proofs required" subsection to `docs/spec.md` (after Phase 2 planning or in layered model table footnote)
- [ ] 2.2 Link to `FAILURE_STANDARDS.md`, blueprint Resilience Contracts anchor, and P6 ship checklist failure injection items

## 3. Patch existing step doc conventions

- [ ] 3.1 Update Prompt conventions in `docs/steps/step0.md` — link FAILURE_STANDARDS.md; note dual ✅ validation requirement for future edits
- [ ] 3.2 Update Prompt conventions in `docs/steps/step1.md` — same link; clarify existing failure bullets are the P1 reference implementation

## 4. P2 skeleton with failure placeholders

- [ ] 4.1 Create `docs/steps/step2.md` header: prerequisites, prompt conventions (with failure link), P2 expansion rationale table from blueprint
- [ ] 4.2 Add step 2.1–2.8 outline entries each with placeholder `─── FAILURE BOUNDARY ───` (cite blueprint 🚨 row) and placeholder `✅ Failure path:` — no full implementation prompts yet

## 5. Verify and close

- [ ] 5.1 Confirm all links resolve (FAILURE_STANDARDS ↔ spec.md ↔ step0/1/2)
- [ ] 5.2 Run `openspec validate step-doc-failure-standards` if available; otherwise manual review
- [ ] 5.3 No `docs/context.md` update required (documentation-only change; no build step completed)
