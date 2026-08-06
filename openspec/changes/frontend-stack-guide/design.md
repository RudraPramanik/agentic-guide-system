## Context

Wandr’s FastAPI backend (P0–P7) exposes destinations, places, planner SSE generate, trips CRUD/GeoJSON/claim, and day-edit routes. Auth uses httpOnly `wandr_token` / `wandr_session` cookies with `SameSite=Lax` (Option A: same registrable domain). CORS defaults include `http://localhost:3000`. There is no frontend in this repo; blueprint marks FE as a separate map. `docs/fe_suggestins.md` proposes a broad 2026 AI SaaS stack. This design locks a Wandr-fit subset and defines how `docs/FE_guide.md` documents it for a sibling Next.js repo that swaps only `NEXT_PUBLIC_API_URL` between local and production API hosts.

## Goals / Non-Goals

**Goals:**

- Publish `docs/FE_guide.md` as the single stack + API-integration contract for the separate Next.js app.
- Prefer industry-standard 2026 choices (App Router, TanStack Query, MapLibre, shadcn) that match our envelopes and SSE.
- Make env-swappable API base URL explicit; keep all DB/Redis/LLM secrets on the backend only.
- Distinguish MVP-locked vs deferred libraries so the first FE build stays shippable.

**Non-Goals:**

- Scaffolding or implementing the Next.js application in this repo.
- Changing FastAPI routes, cookies, or OAuth callback behavior in this change.
- Adopting Better Auth, a Next BFF, WebSockets, file uploads, or admin dashboards for MVP.
- Hosting the frontend (Vercel/etc.) or expanding the VPS production SOP.

## Decisions

### D1 — Separate Next.js repo, not monorepo

- **Choice:** Sibling FE repo; this API repo holds `docs/FE_guide.md` as the contract.
- **Why:** User intent; independent deploy/release; FE only needs a stable `/api/v1` contract.
- **Alternatives:** Monorepo `apps/web` — rejected for now.

### D2 — Core UI stack (locked MVP)

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | Next.js App Router (current stable 15/16 line) | RSC + client islands; industry default |
| Language | TypeScript strict | Required |
| Styling | Tailwind CSS v4 | Fast, matches shadcn |
| Components | shadcn/ui + Lucide | Copy-in primitives; no heavy design system |
| Motion | Motion (Framer Motion lineage) | Generate/progress micro-interactions |
| Forms | React Hook Form + Zod | Client validation aligned with API shapes |
| Server state | TanStack Query v5 | Trips/destinations/mutations/invalidation |
| UI state | Zustand (thin) | Generate wizard, map selection — not Redux |
| Theme | next-themes | Optional light/dark |
| Toasts | Sonner | Errors + claim/edit feedback |
| Dates | date-fns | Lightweight |

- **Alternatives:** SWR (weaker mutation/optimistic story for trip edits); Redux (overkill).

### D3 — Maps: MapLibre + OSM (locked)

- **Choice:** MapLibre GL JS in Client Components; consume `GET /trips/{id}/geojson` + stop polylines.
- **Why:** Travel product core; avoids Google Maps lock-in; matches backend GeoJSON.
- **Alternatives:** Google Maps JS — deferred; Leaflet — acceptable fallback but MapLibre is the 2026 default for vector maps.

### D4 — Planner streaming: custom POST SSE client (not Vercel AI SDK as primary)

- **Choice:** Thin `lib/sse/planner.ts` using `fetch` + ReadableStream parsing of `event:` / `data:` frames. Terminal events: `itinerary_done`, `error`, `clarification_needed`.
- **Why:** Backend emits **tool/phase progress SSE**, not chat token streams. AI SDK optimizes chat/message UIs and would fight our event model.
- **Optional later:** AI SDK only if we add a true chat surface; not for `/planner/generate`.
- **Alternatives:** Force AI SDK adapters — rejected for MVP complexity.

### D5 — Auth: FastAPI owns it; FE is cookie client only

- **Choice:** Browser calls API with `credentials: "include"`. No Better Auth. Login via `GET {API}/api/v1/auth/google`. Session via `/auth/me`.
- **Why:** Cookies are already httpOnly JWT + session; FE must not store tokens in localStorage.
- **Known gap:** OAuth callback currently returns JSON on the API host; FE guide MUST document this and recommend a later API `FRONTEND_URL` redirect — out of scope to implement here.
- **Alternatives:** NextAuth/Better Auth duplicating sessions — rejected (dual source of truth).

### D6 — API layer: domain clients + TanStack Query

- **Choice:** `lib/api/` modules: `auth`, `destinations`, `places`, `planner`, `trips` — not Chat/Notebook/Workspace.
- **Env:** `NEXT_PUBLIC_API_URL` only for API host. Never put `DATABASE_URL` / Redis / LLM keys in FE.
- **Envelope:** Parse `ApiResponse` / `ErrorResponse` / `PaginatedResponse` once in a shared client.
- **Transport:** Direct browser → API (CORS). Next rewrites/BFF deferred unless cookie pain appears.

### D7 — AI UX for Wandr (not generic chat chrome)

MVP UX expectations in the guide:

- Destination search → readiness → compose → generate progress (phase/tool steps) → trip artifact + map → day edit → claim after login.

Defer: conversation branching, regenerate-as-chat, attachments, citation cards, split notebook, Mermaid/LaTeX.

Narrative prose may use `react-markdown` + remark-gfm for day titles/paragraphs only.

### D8 — Quality tooling (locked, light)

- Vitest + React Testing Library; Playwright for smoke (search → generate mock or local API).
- ESLint + Prettier; Husky/lint-staged optional in FE repo.
- Observability: Sentry optional; PostHog deferred until product traffic.

### D9 — `docs/FE_guide.md` structure

The guide SHALL include:

1. Product + repo relationship (sibling FE, env-swappable API)
2. Locked MVP stack table + deferred table (mapped from suggestions)
3. Env vars (FE vs backend checklist)
4. Auth/cookie/CORS rules
5. SSE contract + event names
6. Domain API module map ↔ live endpoints
7. Suggested feature-first folder layout
8. Local docker compose + uvicorn test loop
9. Known gaps (OAuth redirect)

## Risks / Trade-offs

- **[Risk] AI SDK fans expect chat kit → Mitigation:** Guide explicitly says planner SSE ≠ chat stream; show event list.
- **[Risk] OAuth UX broken until API redirect → Mitigation:** Document; ship guest path first; track API follow-up.
- **[Risk] Cross-site cookies if prod domains diverge → Mitigation:** Guide mandates Option A same registrable domain + CORS list.
- **[Risk] Guide drifts from API → Mitigation:** Point at `docs/context.md` Live endpoints; update guide when routes change.
- **[Trade-off] Direct CORS vs BFF →** Simpler MVP; may revisit for same-origin cookies on awkward hosts.

## Migration Plan

1. Land OpenSpec artifacts + write `docs/FE_guide.md` in this repo.
2. Optionally one-line pointer from `docs/context.md` deployment/frontend notes.
3. Scaffold sibling FE repo using the guide (separate change/workstream).
4. Later API change: `FRONTEND_URL` OAuth bounce (not this change).

Rollback: delete or revert `docs/FE_guide.md`; no runtime impact.

## Open Questions

- Exact production hostnames (`app.` / `api.`) — document as placeholders until DNS chosen.
- Whether first FE deploy is Vercel or static on same VPS — hosting out of scope; guide stays host-agnostic.
- Map tile provider (public OSM vs MapTiler key) — recommend OSM for local; note optional key later.
