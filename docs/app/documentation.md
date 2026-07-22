# Wandr — Developer Manual

> **Audience:** Junior and mid-level backend developers onboarding to this repo.  
> **Not for:** End-user / traveler product docs.  
> **Agents:** Still start every session with [`docs/context.md`](../context.md) — this manual is complementary navigation.

**Last refreshed:** 2026-07-22 · **Through step:** P2.2

---

## What this is

A living map of the Wandr backend: **what layers exist and why**, **which files are real vs stubs**, **who imports whom**, and **where to start when you want to change something**.

It does **not** replace:

| Doc | Role |
|-----|------|
| [`docs/context.md`](../context.md) | What’s done / stub / next step (update every validated step) |
| [`AGENT.md`](../../AGENT.md) | Non-negotiable coding rules |
| [`docs/app/system.md`](system.md) | Architecture essays |
| [`docs/app/lld.md`](lld.md) | Pattern catalog |
| [`docs/steps/`](../steps/) | Build prompts + validation |
| [`docs/spec.md`](../spec.md) | OpenSpec workflow playbook |

---

## Recommended read order (first day)

1. [`01-orientation.md`](../manual/01-orientation.md) — how docs fit together  
2. [`02-layers.md`](../manual/02-layers.md) — request path + AI boundary  
3. [`03-module-map.md`](../manual/03-module-map.md) — where is what  
4. [`04-imports-and-wiring.md`](../manual/04-imports-and-wiring.md) — file connections  
5. [`05-how-to-change.md`](../manual/05-how-to-change.md) — recipes when you open a ticket  
6. [`06-maintenance.md`](../manual/06-maintenance.md) — when this manual gets refreshed  

Then skim [`docs/context.md`](../context.md) so you know **P2.3** is next and what is still a stub.

---

## Table of contents

| # | Page | Contents |
|---|------|----------|
| 1 | [Orientation](../manual/01-orientation.md) | Doc layers, who reads what |
| 2 | [Layers & AI boundary](../manual/02-layers.md) | Router→Service→Repo, geo, LLM |
| 3 | [Module map](../manual/03-module-map.md) | Packages/files through P2.2 + stubs |
| 4 | [Imports & wiring](../manual/04-imports-and-wiring.md) | Mermaid + import tables |
| 5 | [How to change](../manual/05-how-to-change.md) | Env, endpoints, geo, migrations, tests |
| 6 | [Maintenance](../manual/06-maintenance.md) | Refresh cadence (phase or every 4–5 steps) |

---

## Snapshot (through P2.2)

- **Running app:** FastAPI (`src/main.py`) — health + Google auth routes  
- **Data:** Postgres/PostGIS, Alembic migrations 001–003, domain models  
- **Geo (real):** Nominatim `geocode()`, Overpass `fetch_pois()`  
- **Not built yet:** place/destination services & routers, OSRM, planner, search, travel_engine logic  

Truth for “is this implemented?” → always [`docs/context.md`](../context.md).
