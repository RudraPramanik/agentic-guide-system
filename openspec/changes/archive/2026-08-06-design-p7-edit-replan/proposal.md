## Why

P6 shipped trip persistence, GeoJSON, claim, and planner SSE, but users still cannot mutate a saved itinerary. Blueprint §P7 defines four day-scoped edit endpoints plus `TripEditEvent` / `user_edited` linkage; `docs/steps/step7.md` is empty and agents would invent layering (calling LangGraph REPLAN tools from CRUD), base-coordinate sources, and reorder semantics. Harden a Cursor build contract now—same pattern as P5/P6—before implementation batches start.

## What Changes

- Author canonical **`docs/steps/step7.md`** as the P7 Cursor build contract (style of `step5.md` / `step6.md`): Decision/Fix Log, shared locks (auth, UoW, failure boundaries, abstractions, design patterns, guardrails), pasteable steps **7.0–7.5**, ✅ proofs, ship criteria, OpenSpec batch list.
- Expand blueprint’s 4 steps into a safe build order: **7.0** base-coords persistence patch → **7.1** service day-surgery → **7.2** router → **7.3** tests → **7.4** `record_edit` → **7.5** smoke + `context.md`.
- Lock product behavior for blueprint endpoints:
  - `PATCH .../stops/reorder`
  - `DELETE .../stops/{place_id}`
  - `POST .../stops` (add)
  - `POST .../reoptimize`
- Lock layering: **TripService → travel_engine + `OsrmRoutingProvider` only** — no `PlannerService`, no `execute_tool`, no LangGraph on edit paths (P5 REPLAN tools remain generation-only).
- Lock failure modes: validation → 422 + rollback; OSRM → haversine / null polyline, HTTP 200; ownership → 403; auth required on all edit routes.
- Add OpenSpec capability specs for the P7 HTTP/edit contract and evaluation `record_edit` behavior.
- **Non-goals:** implementing application code in this change (docs + specs only); chat-driven full-trip replan; evaluation HTTP API; Redis in compose; new packages; changing planner tool loop or SSE generate.

## Capabilities

### New Capabilities
- `p7-trip-edit-replan`: Day-scoped trip edit HTTP API, service day-surgery via travel_engine + RoutingProvider, TripEditEvent audit, validation rollback, auth/ownership matrix.
- `p7-edit-evaluation`: `EvaluationService.record_edit` writes/uses `TripEditEvent` and sets `user_edited=True` when a linked evaluation exists.

### Modified Capabilities
- `trips-repository-service`: Persist `base_lat`/`base_lng` into `Trip.preferences` on `save_from_state` (7.0) so edits can re-route without reinventing PlanRequest; edit ops extend TripService (document expected surface).

## Impact

- **Docs (this change):** `docs/steps/step7.md` created as canonical P7 contract; later `docs/context.md` only on 7.5 implementation apply.
- **Code (future apply batches):** `src/trips/service.py`, `schemas.py`, `router.py`, `repository.py` (as needed); `src/evaluation/service.py` (+ repo helper); `src/core/middleware/rate_limit.py` path table (optional limits); tests under `tests/trips/`; optional `scripts/test_p7_smoke.py`.
- **APIs:** four new authenticated trip day-edit routes returning `ApiResponse[TripOut]`.
- **AGENT.md:** preserves Router→Service→Repository; travel_engine purity via Protocol DI; evaluation records every edit; no LLM on edit path; geo only via `OsrmRoutingProvider` → `geo/osrm`.
- **Efficiency:** day-scoped matrix/polyline only (not full multi-day agent loop); reorder skips TSP permutations.
