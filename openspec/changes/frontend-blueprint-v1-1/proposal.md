## Why

`docs/blueprint_frontend.md` (v1.0) is already the FE build bible, but a critique pass (`docs/front_blueprint_2.md`) exposed real improvisation holes: hand-mirrored types, undefined clarification re-submit, soft sparse-tier gating, AbortController vs “stopped reading,” guest-session-mismatch copy, markdown XSS hygiene, and missing a11y/responsive hardening. We need one corrected SSOT — not two competing blueprints — before scaffolding the sibling Next.js app.

## What Changes

- **Promote corrected v1.1 into `docs/blueprint_frontend.md`** as the sole FE development SSOT (same rigor role as `docs/blueprint_final.md` for backend). Merge `docs/front_blueprint_2.md` content with explore-mode verdict fixes; then remove or clearly supersede the draft so agents cannot pick the wrong file.
- **Adopt v1.1 patch set** (OpenAPI type-lock F0.6, clarification fresh-POST contract, sparse warn+allow, real AbortController + server-cancel proof, guest-session-mismatch copy, narrative markdown sanitization, F7.5/F7.6 a11y+responsive, narrative-cache bound as accepted tradeoff).
- **Correct critique item #4:** destination-search `20/min/IP` **is live** in `RateLimitMiddleware` + settings — treat as a real contract (debounce still good UX); do not mark it “unconfirmed.”
- **Keep wire-contract split:** `docs/FE_guide.md` remains stack + live API contract; `docs/blueprint_final.md` remains backend/planner SSOT — unchanged by this pass except optional cross-links.
- Soft-update `docs/context.md` / `docs/FE_guide.md` pointers if needed so “which bible?” is unambiguous.
- **Non-goals:** scaffolding Next.js; changing FastAPI routes/DTOs; implementing OAuth bounce / narrative persistence / `session_mismatch` error code (those stay Deferred backend follow-ups); rewriting `blueprint_final.md` content; merging FE AGENT rules into backend `AGENT.md`.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `frontend-dev-blueprint`: Raise requirements for v1.1 — OpenAPI-generated wire types, clarification re-submit contract, end-to-end SSE abort integrity, pinned sparse-tier default, distinct guest-session-mismatch UX, LLM markdown sanitization, a11y/responsive hardening steps, and accurate destination-search rate-limit contract (live middleware).

## Impact

- **Docs:** Rewrite `docs/blueprint_frontend.md` to corrected v1.1; retire `docs/front_blueprint_2.md` (delete or one-line stub pointing at SSOT); optional one-line pointers in `docs/FE_guide.md` / `docs/context.md`.
- **OpenSpec:** Delta on `frontend-dev-blueprint`; this change’s planning artifacts.
- **Code / APIs:** none in this repo. Backend stays frozen for FE build; Deferred list documents backend follow-ups only.
- **Coupling:** Blueprint MUST stay aligned with live schemas / `FE_guide.md`; conflict rule unchanged (schemas → OpenAPI → FE_guide → blueprint).
- **AGENT.md:** Backend stays API-only; FE AGENT block lives only in the FE blueprint (sibling-repo paste target).
