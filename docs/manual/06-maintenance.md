# 06 — Maintenance (keep this manual honest)

**Up:** [Developer Manual index](../app/documentation.md) · **Prev:** [05-how-to-change](05-how-to-change.md)

---

## Cadence (locked)

Refresh this developer manual when **either**:

1. A **full phase** finishes (all of P0, P1, P2, …), **or**  
2. **4–5 validated build steps** have landed since the index **Through step** marker  

…whichever comes first.

| Doc | Every step? | On cadence? |
|-----|-------------|-------------|
| `docs/context.md` | **Yes — always** | — |
| `docs/app/documentation.md` + `docs/manual/*` | **No** | **Yes** |
| `AGENT.md` / blueprint | Rare | Rare |

Agents and humans: **do not** rewrite the whole manual after every micro-step. That causes churn and drift.

---

## What to update when refreshing

1. Bump index header: `Last refreshed` + `Through step`  
2. Sync [03-module-map](03-module-map.md) with `context.md` Implemented / Stubs  
3. Extend [04-imports](04-imports-and-wiring.md) only for **new real** wiring (new routers, gateways)  
4. Add recipes to [05-how-to-change](05-how-to-change.md) if a new pattern appeared (e.g. seed script)  
5. Keep [02-layers](02-layers.md) accurate if a new layer became real (planner, search, …)  

---

## What not to duplicate

| Don’t copy into the manual | Keep instead |
|----------------------------|--------------|
| Full AGENT.md rule list | Link + short reminders |
| Step-by-step build prompts | `docs/steps/` |
| Entire blueprint | `docs/blueprint_final.md` |
| Every OpenSpec SHALL | `openspec/specs/` |
| Long architecture essays | `system.md` / `lld.md` |

Prefer **links and tables** over prose.

---

## Sanity checklist before you finish a refresh

- [ ] Every row in `context.md` **Implemented modules** appears as real in module map  
- [ ] Every **stub** called out in context is marked stub in module map / wiring  
- [ ] No recipe tells juniors to import a stub API  
- [ ] Index TOC links still resolve  

---

## Refresh log

| Refreshed | Through step | Trigger |
|-----------|--------------|---------|
| 2026-07-22 | P2.2 | Manual v1 written |
| 2026-07-26 | P2.4 | Cadence — 2.3, 2.6a, 2.6b, 2.4 landed since the P2.2 marker |
| 2026-07-26 | P2.8 | Cadence — 2.5→2.8 (OSRM, destinations/places HTTP, readiness) |
| 2026-07-26 | P2.10 | P2 phase complete — 2.9 pytest + 2.10 smoke |
| 2026-07-30 | P4.10 | P3+P4 catch-up — search/enrich/index + travel_engine + CORS + tools envelope + p4 smoke |
| 2026-07-31 | P5.11 | Cadence — P5.1–5.11 (tools + graph loop + narrative/eval + compile); 5.12–5.14 not yet context-✅ |
| 2026-08-06 | P6.5 | P5+P6 catch-up — PlannerService/SSE/trips HTTP/cache backends + p6 smoke; Next → P7.1 |
| 2026-08-27 | P7 + V6.1 | P7 + post-P7/v7 catch-up — trip day edits, Langfuse generate wrap, golden harness, hybrid search; evaluation HTTP still stub |

Next natural refresh: when the next full phase completes, or after ~4–5 validated steps since this marker.
