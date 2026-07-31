# Wandr — Developer Manual

> **Audience:** Junior and mid-level backend developers onboarding to this repo.  
> **Not for:** End-user / traveler product docs.  
> **Agents:** Still start every session with [`docs/context.md`](../context.md) — this manual is complementary navigation.

**Last refreshed:** 2026-07-31 · **Through step:** P5.11

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

Then skim [`docs/context.md`](../context.md) so you know **P5.12** is next (PlannerService SSE bridge + tests/smoke) and what is still a stub.

---

## Table of contents

| # | Page | Contents |
|---|------|----------|
| 1 | [Orientation](../manual/01-orientation.md) | Doc layers, who reads what |
| 2 | [Layers & AI boundary](../manual/02-layers.md) | Router→Service→Repo, geo, LLM, travel_engine, planner loop |
| 3 | [Module map](../manual/03-module-map.md) | Packages/files through P5.11 + stubs |
| 4 | [Imports & wiring](../manual/04-imports-and-wiring.md) | Mermaid + import tables |
| 5 | [How to change](../manual/05-how-to-change.md) | Env, endpoints, geo, enrich, planner, migrations, tests |
| 6 | [Maintenance](../manual/06-maintenance.md) | Refresh cadence (phase or every 4–5 steps) |

---

## Snapshot (through P5.11)

- **Running app:** FastAPI (`src/main.py`) — health + auth + destinations + places; CORS; lifespan DB ping + Qdrant ensure + MiniLM load  
- **Data:** Postgres/PostGIS, Alembic migrations 001–004 (`places.enriched_tags`), domain models  
- **Geo (real):** Nominatim `geocode()`, Overpass `fetch_pois()`, OSRM `get_route()`  
- **Catalog HTTP:** destinations search + readiness; places list/get (paginated)  
- **Search / enrich (P3):** Qdrant client + MiniLM embeddings + `places_index`; `PlaceService.enrich_place`; enrich/index scripts  
- **Travel engine (P4):** pure Python selector → allocator → optimizer → schedule → validator; no network/DB/LLM  
- **Planner (P5.1–5.11):** phase-gated 12-tool registry + orchestration; `TravelState`; agent↔tool_executor loop; narrative + evaluation bookends; compiled graph singleton  
- **Evaluation:** `EvaluationRepository` / `EvaluationService.record_generation` real for planner bookend  
- **Seeding:** `scripts/seed_destination.py` — use `--radius 50` if you need ~100+ places for limited-band readiness  
- **Verification:** pytest **149** (`tests/…` incl. planner phase transitions + `chat_with_tools`) + `scripts/test_p2_smoke.py` + `scripts/test_p4_smoke.py`  
- **Not validated yet (next):** PlannerService SSE bridge (5.12), tool-loop pytest suite (5.13), `scripts/test_agent.py` + context closeout (5.14)  
- **Not built yet:** trips CRUD HTTP; `POST /api/v1/planner/generate` (P6); `auth/dependencies.py`  

Truth for “is this implemented?” → always [`docs/context.md`](../context.md).
