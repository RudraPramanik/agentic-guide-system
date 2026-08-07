## Context

Wandr backend P0–P7 is complete. Live API covers destinations, places, planner SSE, trips CRUD/GeoJSON/claim, and day-edit. Auth is httpOnly cookie Option A (`wandr_token` / `wandr_session`, `SameSite=Lax`, same registrable domain).

`docs/FE_guide.md` already locks the sibling-Next.js stack and wire contract (envelopes, SSE, GeoJSON, auth matrix, DTOs). What is missing is the **frontend equivalent of `docs/blueprint_final.md`**: a failure-first, phased development bible with AGENT guardrails, resilience contracts, and per-step proofs — so the FE repo is not built as a happy-path demo.

This change authors that document in the API repo (contract home). Application code remains in a future sibling FE repo.

## Goals / Non-Goals

**Goals:**

- Publish `docs/blueprint_frontend.md` as FE development SSOT (principles → AGENT → structure → resilience → F-phases → failure summary → package order).
- Match backend blueprint *rigor* (not copy Python internals): every step has pattern + failure boundary + proof; no happy-path-only design.
- Keep `FE_guide.md` as stack/API contract; blueprint references it and does not fork DTO truth.
- Lock MVP handling of known gaps (narrative durability, OAuth return, no evaluation HTTP).
- Provide a copy-ready FE `AGENT.md` block for the sibling repo.

**Non-Goals:**

- Scaffolding or implementing the Next.js app in this change.
- Changing FastAPI routes, cookies, OAuth callback, or persisting narratives on `TripOut`.
- Merging FE rules into backend `AGENT.md`.
- Frontend hosting / Vercel / expanding `blueprint_production.md`.
- Replacing or rewriting `FE_guide.md` wholesale (one-line cross-link OK).

## Decisions

### D1 — Document home: `docs/blueprint_frontend.md` in the API repo

- **Choice:** FE bible lives beside `FE_guide.md` and `blueprint_final.md` in `guideagent`.
- **Why:** Single contract home; agents already start from this repo’s docs; sibling FE repo can symlink or copy AGENT + read remote docs.
- **Alternatives:** Put bible only in FE repo — rejected until FE repo exists; would orphan the contract.

### D2 — Two-doc split (contract vs build)

| Doc | Role |
|-----|------|
| `FE_guide.md` | Locked stack + live API mirror (what to call, how envelopes/SSE/auth work) |
| `blueprint_frontend.md` | How to build in phases with principles, fallbacks, proofs |
| `blueprint_final.md` | Backend/planner SSOT — unchanged |

- **Conflict rule:** schemas → OpenAPI → `FE_guide.md` → blueprint. Blueprint loses on wire-shape disputes.

### D3 — Principles (locked set for the doc)

Numbered principles the blueprint MUST ship (wording can polish, intent fixed):

1. **Packages at point of use** — install only in the F-step that needs them.
2. **Pattern named per step** — every step cites an FE/LLD pattern (Gateway client, Query cache, Null UI, Abortable stream, etc.).
3. **Failure boundary per step** — every external call / stream / tile load has a named fallback UI.
4. **Env-swappable API** — same build; only `NEXT_PUBLIC_API_URL` (+ map style) changes.
5. **Lightest viable package** — no Redux, no AI SDK as planner client, no BFF unless cookie pain proves it.
6. **Trip is the durable artifact** — not a chat notebook shell.
7. **FastAPI owns auth** — FE is cookie client only.
8. **Server state in Query; UI state thin** — Zustand for wizard/map selection only.
9. **Controlled AI-assisted FE** — FE `AGENT.md` prevents uncontrolled Cursor output.
10. **Envelope discipline** — one client parses success/error; special-case pagination/GeoJSON/SSE/204.
11. **Streams are abortable** — navigate-away cancels generate; no zombie readers.
12. **Types follow the backend** — do not invent fields (`search_available` on readiness, etc.).
13. **Degrade the map, don’t blank the trip** — missing polylines → points only; tile fail → list-first UI.

### D4 — Phase map (F0–F7)

Aligned to product shell, guest-first:

```
F0 Scaffold + AGENT + api client + providers
        ↓
F1 Session shell (/me, guest, login CTA)
        ↓
F2 Search + readiness gate
        ↓
F3 Compose + SSE generate (progress + terminals)
        ↓
F4 Trip view + MapLibre GeoJSON
        ↓
F5 Claim + my trips (auth surfaces; OAuth gap documented)
        ↓
F6 Day edit + Query invalidation
        ↓
F7 Hardening (errors, 429 UX, tests, smoke)
```

Each phase uses the same legend as backend: 📦 🏗️ 🚨 ☁️ 🔒 ✅

### D5 — Resilience contracts (FE-shaped)

Not tenacity/httpx — browser-side equivalents:

| Surface | Timeout / abort | Retry | Named fallback |
|---------|-----------------|-------|----------------|
| JSON API | `AbortSignal` + sensible default (e.g. 15–30s) | Idempotent GETs: 1 bounded retry optional; mutations: no blind retry | Toast from `ErrorResponse.code`; empty/error panel |
| SSE generate | Abort on unmount; respect backend ~45s ceiling | No auto-retry whole generate without user action | Progress → error panel; 409 readiness → gate UI |
| Map style/tiles | MapLibre error events | Provider fallback only in **dev** (OSM) | Trip list/day UI remains usable |
| GeoJSON | Same as JSON API | — | Points-only / “route unavailable” |
| `/auth/me` | Same as JSON API | 1 retry on network blip | Treat as guest; show reconnect |

Rate limits: map `rate_limit_exceeded` to Sonner + disable CTA briefly — never infinite spin.

### D6 — MVP narrative rule (locked)

**Choice for blueprint MVP:** Option A — capture day `title`/`narrative` from terminal `itinerary_done` into **session UI state** (Zustand or Query cache keyed by `trip_id`) for the generate→trip session; hard reload may lose prose; `GET /trips/{id}` remains geometry/schedule source of truth.

- **Why:** Matches current backend (narratives not on `TripOut`); allows markdown UX without inventing APIs.
- **Follow-up (out of scope):** backend persist narratives on trip or preferences JSON.
- **Forbidden:** fake narrative endpoints; treating full SSE blob as long-term model without calling out reload loss.

### D7 — OAuth / claim sequencing

- Guest path F0–F4 ships without polished login return.
- F5 documents incomplete OAuth (API returns JSON on callback host) and defines CTA copy: “Login may leave you on API host until FRONTEND_URL bounce lands.”
- Claim flow still specified against real `POST /trips/{id}/claim` + cookie rules for when login works (local same-site or after bounce).

### D8 — FE AGENT.md location

- Full text lives **inside** `blueprint_frontend.md` (like backend blueprint embeds AGENT).
- Apply step: also note “on FE repo scaffold, write this file to FE root” — not written into backend `AGENT.md`.

### D9 — Step density

- Prefer fewer phases with clear substeps over copying backend’s 70+ micro-steps verbatim.
- Target ~25–40 F-steps total across F0–F7 — enough for Cursor sessions, not a novel.
- Each step’s ✅ is runnable in FE repo (`npm run typecheck`, Vitest, Playwright, or manual checklist tied to local API).

### D10 — LLD / FE pattern catalog (include in doc)

At minimum name and use:

| Pattern | Where |
|---------|--------|
| API Gateway client | `lib/api/client.ts` |
| Domain modules | `lib/api/{auth,destinations,places,planner,trips}` |
| Envelope Adapter | success/error/pagination/geojson/sse parsers |
| Abortable Stream | planner SSE |
| Server-state cache | TanStack Query keys + invalidation on edit/claim |
| Thin UI store | Zustand wizard/map |
| Null / empty UI | readiness sparse, empty trips, map no-lines |
| Cookie session probe | `/auth/me` |
| Feature folders | `features/*` over dump `components/` |

### D11 — Context.md touch

One short bullet under deployment/frontend notes:

> FE phased build bible: `docs/blueprint_frontend.md` (stack/API contract remains `docs/FE_guide.md`).

No Progress table rows for F-phases.

### D12 — Optional one-line FE_guide cross-link

At top of `FE_guide.md`: “Phased build: see `docs/blueprint_frontend.md`.” No structural rewrite.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Blueprint duplicates/forks `FE_guide` wire details | Conflict rule + “reference §N of FE_guide” instead of re-listing every DTO field |
| Over-long doc (backend is 1500+ lines) | Cap F-steps; put DTO sketches only by reference to FE_guide §14–15 |
| Narrative Option A surprises users on reload | Explicit UX copy + deferred backend follow-up called out in Deferred section |
| Agents edit backend AGENT.md | Spec forbids it; blueprint states FE AGENT is sibling-repo only |
| FE repo not created yet → blueprint unused | Still valuable as SSOT before scaffold; F0 is the scaffold recipe |
| context.md `search_available` drift confuses FE | Blueprint + FE_guide already correct; optional note “do not trust stale context wording” under readiness — fix context in a tiny same-PR doc fix if touched |

## Migration Plan

1. Land OpenSpec artifacts (this change).
2. On `/opsx:apply`: author `docs/blueprint_frontend.md`, add context (+ optional FE_guide) pointers.
3. No runtime migration. Rollback = delete/revert the markdown files.
4. Later: scaffold FE repo using F0; archive this change when doc is validated against checklist.

## Open Questions

Resolved in this design (no blockers):

- Narrative MVP → Option A (session cache from SSE).
- Doc path → `docs/blueprint_frontend.md`.
- Phase count → F0–F7.

Deferred to apply-time polish only:

- Exact day estimates per phase (optional Timeline Summary like backend).
- Whether to add `docs/steps/fe/step*.md` later — **out of scope**; keep steps inside the single bible for MVP (backend historically used both; FE starts bible-only to avoid doc sprawl).
