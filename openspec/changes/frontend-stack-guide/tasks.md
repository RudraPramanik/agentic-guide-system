## 1. Author FE_guide.md

- [x] 1.1 Write `docs/FE_guide.md` intro: sibling Next.js repo, env-swappable `NEXT_PUBLIC_API_URL`, pointer that `docs/fe_suggestins.md` is input only
- [x] 1.2 Add locked MVP stack table (Next App Router, TS, Tailwind v4, shadcn, Lucide, Motion, RHF+Zod, TanStack Query, Zustand UI-only, next-themes, Sonner, date-fns, MapLibre)
- [x] 1.3 Add deferred/rejected table (AI SDK primary planner, Better Auth, chat-notebook shell, Table/Recharts, WebSockets, uploads, Mermaid/LaTeX)
- [x] 1.4 Document FE vs backend env split; forbid DB/Redis/LLM secrets in FE
- [x] 1.5 Document cookie/CORS Option A + `credentials: "include"` + no localStorage tokens
- [x] 1.6 Document planner SSE: POST `fetch` parser, terminal events, no `EventSource`
- [x] 1.7 Map domain API modules (auth/destinations/places/planner/trips) to live endpoints from `docs/context.md`
- [x] 1.8 Document MVP screen flow (search → ready → compose → generate → trip+map → claim/edit)
- [x] 1.9 Document local loop (compose + uvicorn + seed + Next `:3000`)
- [x] 1.10 Document OAuth callback gap + future `FRONTEND_URL` follow-up
- [x] 1.11 Add suggested feature-first folder layout for the sibling FE repo

## 2. Cross-links

- [x] 2.1 Add a short pointer to `docs/FE_guide.md` in `docs/context.md` deployment/frontend notes (no progress-table churn)
- [x] 2.2 Optionally note at top of `docs/fe_suggestins.md` that FE_guide is the locked subset (one-line banner)

## 3. Validate

- [x] 3.1 Re-read `docs/FE_guide.md` against Live endpoints in `docs/context.md` — no invented routes
- [x] 3.2 Confirm guide non-goals: no FE scaffold in this repo, no API code changes in this change
