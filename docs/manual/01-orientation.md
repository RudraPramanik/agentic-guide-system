# 01 — Orientation

**Up:** [Developer Manual index](../app/documentation.md)

---

## What Wandr is (one paragraph)

Wandr is a **FastAPI modular monolith** that generates multi-day travel itineraries. Structure (places, routes, times) comes from **code**; narrative prose comes from an **LLM** outside the tool loop. Today (through **P5.11**) you have: app scaffold, auth, database models, geo gateways, destination/place HTTP APIs with readiness, seed + enrich + index CLIs, Qdrant search, pure `travel_engine`, CORS, and the phase-gated LangGraph planner (tools + agent↔executor loop + narrative/eval bookends + compiled graph). Next product work is **P5.12** (PlannerService SSE bridge), then 5.13–5.14 (tool-loop tests + agent smoke), then **P6** HTTP generate.

---

## How documentation layers relate

```text
┌─────────────────────────────────────────────────────────────┐
│  docs/context.md     ← “Where are we?” (agents + humans)   │
│  AGENT.md            ← “What must never be violated?”      │
├─────────────────────────────────────────────────────────────┤
│  docs/app/documentation.md + docs/manual/*                 │
│                      ← “Where is what / how do I change?”  │
├─────────────────────────────────────────────────────────────┤
│  docs/app/system.md  ← architecture (why the system)       │
│  docs/app/lld.md     ← patterns (how we implement)         │
├─────────────────────────────────────────────────────────────┤
│  docs/steps/step*.md ← build prompts for the next slice    │
│  docs/blueprint_final.md ← north-star product plan         │
├─────────────────────────────────────────────────────────────┤
│  openspec/changes/*  ← active planning for one slice       │
│  openspec/specs/*    ← permanent behavior after archive    │
│  docs/spec.md        ← how to use OpenSpec in this repo    │
└─────────────────────────────────────────────────────────────┘
```

| You want… | Open first |
|-----------|------------|
| Is feature X already built? | `docs/context.md` (Implemented / Stubs) |
| Can I call Overpass from a router? | `AGENT.md` (no — only via `src/geo/`) |
| How does auth flow through files? | This manual → [04-imports](04-imports-and-wiring.md) |
| Deep design of repositories | `docs/app/lld.md` |
| Exact build instructions for step 2.3 | `docs/steps/step2.md` |
| Propose/apply a change with Cursor | `docs/spec.md` + `/opsx:propose` |

---

## Who maintains what

| Doc | Update frequency |
|-----|------------------|
| `docs/context.md` | **Every** validated build step |
| This developer manual | Full phase end **or** every **4–5** steps ([06-maintenance](06-maintenance.md)) |
| `AGENT.md` / blueprint | Rare — team decision |
| OpenSpec change artifacts | Per feature slice |

---

## Local mental model

1. **HTTP** hits FastAPI routers in domain packages (`src/auth/router.py`, `src/destinations/router.py`, `src/places/router.py`).  
2. Routers call **services**; services call **repositories** (never skip layers).  
3. **External geo** (Nominatim, Overpass, OSRM) only inside `src/geo/`.  
4. **LLM** only inside `src/core/llm/client.py`; **search** only via `src/search/`; **scheduling math** only via `src/travel_engine/` (pure).  
5. If a file is listed under **Stubs** in `context.md`, it has **no public API** — don’t import it expecting logic. PlannerService SSE bridge (5.12) and planner HTTP generate (P6) are still not context-✅ / not built.

Next: [02 — Layers & AI boundary](02-layers.md)
