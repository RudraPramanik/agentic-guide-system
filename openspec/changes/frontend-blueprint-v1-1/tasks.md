## 1. Promote corrected FE bible

- [x] 1.1 Replace `docs/blueprint_frontend.md` with corrected v1.1 content sourced from `docs/front_blueprint_2.md` plus design D2–D9 (especially live destination-search rate-limit wording — not “unconfirmed”)
- [x] 1.2 Ensure header marks **Supersedes v1.0**, includes “What changed vs v1.0” table, and states sole FE build SSOT role (parallel to `docs/blueprint_final.md` for backend)
- [x] 1.3 Verify AGENT block, principles #11–15, F0.6, F2.1/F2.2, F3.2/F3.3, F4.1, F7.5/F7.6, Deferred gaps, and timeline (~15.5–19d) match the delta spec

## 2. Retire dual bible

- [x] 2.1 Delete `docs/front_blueprint_2.md` **or** replace it with a short stub that only points to `docs/blueprint_frontend.md` (no competing phased content)
- [x] 2.2 Grep docs/openspec for `front_blueprint_2` references and update or remove them

## 3. Cross-links and pointers

- [x] 3.1 Confirm `docs/FE_guide.md` points at `blueprint_frontend.md` for phased build (one-line cross-link OK; do not fork DTOs)
- [x] 3.2 Soft-update `docs/context.md` FE/deployment notes to the single bible if needed — no Progress-table churn treating F-phases as backend steps
- [x] 3.3 Leave `docs/blueprint_final.md` content unchanged (backend SSOT only); add a one-line FE pointer only if a natural doc-relationship spot already exists

## 4. Verify against live contract

- [x] 4.1 Spot-check F2.1 rate-limit text against `src/config.py` + `src/core/middleware/rate_limit.py` (search path + 20/min)
- [x] 4.2 Spot-check clarification / AbortController / terminals against `docs/FE_guide.md` §7–8 and `src/planner/router.py` disconnect poll
- [x] 4.3 Run a quick consistency pass: conflict rule still schemas → OpenAPI → FE_guide → blueprint; no invented endpoints

## 5. Close-out

- [x] 5.1 Self-check OpenSpec delta scenarios are satisfied by the published bible (single file, type-lock, clarification, abort, sparse, session-mismatch, markdown, a11y/responsive)
- [x] 5.2 Mark this change ready to archive after apply; no application code or API changes in this pass
