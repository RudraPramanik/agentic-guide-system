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

## Explicit refresh now

This v1 was written at **P2.2**. Next natural refresh candidates:

- After **P2.3–P2.7** (~places repo + destinations + seed), or  
- When **P2** phase completes  

Whichever hits the cadence rule first.
