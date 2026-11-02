## 1. Baseline facts

- [x] 1.1 Re-read `docs/context.md` (Current state, Stubs only, Live endpoints, Local dev quick ref) and note facts that must appear in `system.md`
- [x] 1.2 Grep current `docs/app/system.md` for stale phrases (`No domain routers`, `No X-Request-ID`, Redis-off-only, `through P6.5`, package version pins) to ensure the rewrite eliminates them

## 2. Rewrite system.md

- [x] 2.1 Replace `docs/app/system.md` with a durable architecture outline: purpose, layering diagram, domain/package map, request path (Router→Service→Repository + envelopes), planner tool-loop + SSE generate, search (hybrid/`places_v2`), routing backends (`haversine`/`hybrid`/`osrm`), trips CRUD + day edit, observability + golden evals
- [x] 2.2 Document local Compose infra accurately (Postgres :5433, Qdrant :6335, Redis host :6380, API :8000) and empty-`REDIS_URL` vs Compose-injected Redis
- [x] 2.3 Add explicit stubs/deferred section matching context (evaluation HTTP, `auth/dependencies.py`, V6.2/V6.3 deferred); link out for API detail (`docs/FE_guide.md`) and step progress (`docs/context.md`)
- [x] 2.4 Replace Build Progress with a one-line phase rollup (P0–P7 + V0–V6.1 ✅; next = VPS deploy) — do not clone the Progress table; remove package version pins

## 3. Honesty check

- [x] 3.1 Verify `system.md` no longer contains the stale phrases from 1.2 and does not invent stub APIs
- [x] 3.2 Spot-check `docs/app/lld.md` for any remaining claim that contradicts post-P7 / V6.1 context; apply a minimal one-line fix only if needed (otherwise leave unchanged)
- [x] 3.3 Confirm no application code, `documentation.md` / `docs/manual/`, or unrelated docs were changed
