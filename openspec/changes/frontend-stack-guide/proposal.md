## Why

Backend P7 is complete and the product needs a separate production-ready Next.js frontend that talks to FastAPI via a single env-swappable `API_URL`. A generic AI SaaS stack draft exists in `docs/fe_suggestins.md`, but it mixes chat-notebook patterns with travel-planner needs. We need a locked, Wandr-specific frontend stack guide in `docs/FE_guide.md` before scaffolding the sibling FE repo — so agents and humans build against one contract (cookies, SSE, envelopes, maps) instead of reinventing per session.

## What Changes

- Add `docs/FE_guide.md` as the canonical frontend stack + integration guide (separate Next.js repo; not a monorepo).
- Lock MVP core stack: Next.js (App Router) + TypeScript + Tailwind v4 + shadcn/ui + TanStack Query + Zustand (UI only) + MapLibre + Zod/RHF + Sonner.
- Document FastAPI auth/cookie/CORS/SSE contracts the FE must honor (`credentials: "include"`, POST `fetch` SSE — not `EventSource`, `ApiResponse` envelope).
- Trim `docs/fe_suggestins.md` ideas that do not fit Wandr MVP (Better Auth, Vercel AI SDK as primary planner client, notebook/workspace APIs, WebSockets, file uploads, heavy dashboards).
- Note a small future API follow-up (OAuth success → `FRONTEND_URL` redirect) without implementing it in this change.
- Optionally add a short pointer in `docs/context.md` to `docs/FE_guide.md` under deployment/frontend notes (no phase/progress table churn).

## Capabilities

### New Capabilities

- `frontend-stack-guide`: Canonical requirements for Wandr’s separate Next.js frontend stack, env-swappable API base URL, domain API client shape, streaming/map/auth integration rules, and MVP vs deferred libraries.

### Modified Capabilities

- (none — documentation/contract for a new FE surface; no backend requirement deltas)

## Impact

- **Docs:** `docs/FE_guide.md` (new); references `docs/fe_suggestins.md` as input; may point from `docs/context.md`.
- **OpenSpec:** `openspec/changes/frontend-stack-guide/` planning artifacts.
- **Code:** none in this change (no FE scaffold, no API code). FE implementation happens in a separate repo after this guide lands.
- **Backend coupling:** FE must match existing live endpoints and cookie/CORS Option A; OAuth post-login redirect remains a known gap until a later API change.
- **Non-goals:** scaffolding the Next.js app; VPS/frontend hosting; Better Auth; monorepo; changing FastAPI routes; Redis/DB env in the frontend.
