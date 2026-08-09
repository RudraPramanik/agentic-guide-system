## Context

`docs/blueprint_frontend.md` v1.0 already exists as the FE development bible (OpenSpec `frontend-blueprint`, capability `frontend-dev-blueprint`). A critique draft (`docs/front_blueprint_2.md`) proposed a v1.1 patch pass. Explore-mode review accepted most of that patch and corrected one claim: destination-search `20/min/IP` is **already live** in `RateLimitMiddleware` + settings — not “unconfirmed.”

Today agents can open either v1.0 or the draft and diverge. This change collapses them into one corrected SSOT and raises the OpenSpec requirements so future drifts are testable.

Doc roles stay split (same as backend pattern in `docs/blueprint_final.md` vs app docs):

| Doc | Role after this change |
|-----|------------------------|
| `docs/blueprint_frontend.md` | **Sole** FE build bible (v1.1 corrected) |
| `docs/FE_guide.md` | Stack + live API wire contract (unchanged) |
| `docs/blueprint_final.md` | Backend / planner SSOT (unchanged) |
| `docs/front_blueprint_2.md` | Retired (deleted or stub → SSOT) |

## Goals / Non-Goals

**Goals:**

- Replace `docs/blueprint_frontend.md` content with corrected v1.1 (from `front_blueprint_2.md` + verdict).
- Eliminate dual-bible ambiguity.
- Encode new contracts in `frontend-dev-blueprint` requirements (types, clarification, abort integrity, sparse default, session-mismatch UX, markdown hygiene, a11y/responsive, accurate search rate limit).
- Keep Deferred backend follow-ups documented (OAuth bounce, narrative persistence, `session_mismatch` error code) without implementing them.

**Non-Goals:**

- Scaffolding or implementing the Next.js app.
- Changing FastAPI routes, cookies, OpenAPI shape, or error codes.
- Rewriting `blueprint_final.md` or the developer manual.
- Merging FE AGENT rules into backend `AGENT.md`.
- Automated axe-core CI (stays deferred beyond F7.5).

## Decisions

### D1 — Single file promotion, not parallel versions

- **Choice:** Overwrite `docs/blueprint_frontend.md` with corrected v1.1; retire `docs/front_blueprint_2.md`.
- **Why:** One path for agents; mirrors how `blueprint_final.md` is the sole backend bible.
- **Alternatives:** Keep both with “see v1.1” header — rejected (agents still pick the wrong file).

### D2 — Verdict override on search rate limit

- **Choice:** Document destination-search `20/min/IP` as a **live** middleware contract (`RATE_LIMIT_DESTINATIONS_SEARCH_*` + `RateLimitMiddleware`). FE still debounces for UX; 429 handling is real and may be proven.
- **Why:** Critique #4 checked phase checklists, not live `src/core/middleware/rate_limit.py`. Soft-guidance-only would under-test a working limiter.
- **Alternatives:** Keep “unconfirmed” wording — rejected as factually wrong against current code.

### D3 — OpenAPI type-lock (F0.6)

- **Choice:** `openapi-typescript` → `types/generated/api.d.ts` (committed); domain types in `types/` compose/narrow. SSE event unions remain hand-authored overlays (OpenAPI often under-specifies stream frames).
- **Why:** Hand-mirrored DTOs already failed once (DashNotes lesson). Codegen for JSON routes; explicit hybrid for SSE.
- **Alternatives:** Hand types only — rejected. Full generated SSE — not reliable from current OpenAPI.

### D4 — Clarification = fresh generate, append to `raw_input`

- **Choice:** On `clarification_needed`, UI collects answer; re-POST `/planner/generate` with `raw_input = original + "\n" + answer`, new `AbortController`, reset progress. No resume.
- **Why:** Backend has no resume endpoint; terminals are one-shot. Fresh graph run is the only contract.
- **Note:** Exact join format (`\n`) is the locked MVP default; product copy can polish later without inventing APIs.

### D5 — End-to-end abort integrity

- **Choice:** Require real `AbortController` passed into `fetch` (not only breaking the reader loop). F3.2 proof includes confirming server task cancels via `request.is_disconnected()`; F7.3 adds navigate-away smoke proxy.
- **Why:** Orphaned generations burn LLM budget; backend already polls disconnect.

### D6 — Sparse tier: warn + allow

- **Choice:** `ready` / `limited` / `sparse` all allow generate; escalating inline warnings. Hard floor remains backend `409 destination_not_ready`.
- **Why:** Removes untestable “per product copy”; preserves guest path.

### D7 — Guest-session-mismatch UX (FE context stopgap)

- **Choice:** Distinct copy for guest viewing another session’s trip vs authenticated ownership failure; differentiate by viewer auth state until backend adds `session_mismatch` (or similar) code.
- **Why:** Login CTA for session mismatch misleads. Backend body is identical `forbidden` today.
- **Risk accepted:** Stale `/auth/me` can mis-label; Deferred backend code is the real fix.

### D8 — Markdown sanitization + F7 a11y/responsive

- **Choice:** AGENT hard rule: `react-markdown` + `remark-gfm` only; no `rehype-raw` / `dangerouslySetInnerHTML` for LLM narrative. F7.5 keyboard/ARIA-live; F7.6 breakpoints + map collapse on small viewports.
- **Why:** Security + shippable UX without redesigning F0–F6.

### D9 — Timeline honesty

- **Choice:** Publish ~15.5–19 day FE-only estimate (was ~13–16) reflecting F0.6, clarification, abort proof, F7.5/F7.6.
- **Why:** Prefer honest schedule over cutting hardening silently.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Agents still open `front_blueprint_2.md` | Delete or replace with stub that points only to `blueprint_frontend.md` |
| OpenAPI codegen fails without running API | Commit generated types; script fails loud if `/openapi.json` unreachable |
| SSE types incomplete in OpenAPI | Domain overlay unions; do not pretend codegen covers stream frames |
| 403 differentiation by guest vs user is fragile | Document as stopgap; Deferred `session_mismatch` code |
| F7.5/F7.6 get cut under schedule pressure | Principle #15 + named steps with proofs; axe CI stays deferred so MVP bar is manual pass |
| Clarification `\n` append confuses preference parser | One live spike during F3; adjust join format in blueprint if needed — still fresh POST |

## Migration Plan

1. Write corrected v1.1 into `docs/blueprint_frontend.md` (header: Supersedes v1.0; changelog table).
2. Retire `docs/front_blueprint_2.md`.
3. Ensure `docs/FE_guide.md` / `docs/context.md` point at the single FE bible (no Progress-table churn).
4. Archive this OpenSpec change after tasks complete; sync delta into `openspec/specs/frontend-dev-blueprint/`.

Rollback: restore prior `blueprint_frontend.md` from git; reintroduce draft only if needed.

## Open Questions

- None blocking. Clarification join-string polish can happen during F3 implementation without a new design pass.
- Backend `session_mismatch` error code and OAuth `FRONTEND_URL` bounce remain separate backend changes (Deferred list only).
