## Context

P6 is complete (`docs/context.md`: Next = P7.1). Trips CRUD, GeoJSON, claim, planner SSE, and polyline geometry all work. `TripEditEvent` + `EditType` exist since 1.9; `TripEvaluation.user_edited` exists; `EvaluationService.record_edit` does **not**. Blueprint §P7 is a thin endpoint table + four bullets; `docs/steps/step7.md` is empty.

Critical code facts:
- `Trip` has **no** `base_lat`/`base_lng` columns — generation base lived only on `TravelState` / `PlanRequest`.
- `TripService` must not call `PlannerService` (P6 lock).
- P5 REPLAN tools (`reoptimize_routes`, etc.) mutate `TravelState` inside LangGraph — different product surface from user HTTP edits.
- Place coords come from PostGIS via `geoalchemy2.shape.to_shape` (`.y`=lat, `.x`=lng).
- `UniqueConstraint(trip_id, place_id)` — a place cannot appear twice on one trip.
- `optimize_route` permutes; reorder must **not** call it if the user supplied order.

This change is **docs + specs only**: produce a P5/P6-quality Cursor contract in `docs/steps/step7.md`. Application code lands in later apply batches.

## Goals / Non-Goals

**Goals:**

- Write `docs/steps/step7.md` as the canonical P7 build contract (Decision/Fix Log, principles, failure modes, abstractions, pasteable 7.0–7.5 prompts, ✅, ship criteria, OpenSpec batches).
- Lock layering, per-op semantics, base-coords strategy, validation/rollback, auth, and evaluation audit so implementers do not invent.
- Align with `AGENT.md`, blueprint §P7 endpoints, and existing travel_engine / RoutingProvider / trips patterns.

**Non-Goals:**

- Implementing `src/trips` edit code, routers, or tests in **this** change.
- Re-entering LangGraph / calling `execute_tool` on edit.
- Chat-driven “replan my whole trip” product.
- Evaluation HTTP API; new DB tables/migrations (preferences JSON only for base coords); new packages.
- Rewriting blueprint §P7 prose (contract interprets it; blueprint remains SoT for product intent).

## Decisions

### D1 — Canonical artifact = `docs/steps/step7.md` (like harden-p6)

**Decision:** This planning change’s apply task writes the full step7 Cursor contract. Implementers read `step7.md` only (plus `AGENT.md` / `context.md`).  
**Alternatives:** Implement from blueprint table alone → rejected (P6 polyline/claim gaps). Suggestion file first → optional later; not required if design locks are complete here.

### D2 — Build order 7.0 → 7.5 (blueprint 7.1–7.4 expanded)

| Step | Deliverable |
|------|-------------|
| **7.0** | Persist `base_lat`/`base_lng` into `Trip.preferences` on `save_from_state`; helpers to resolve base for edits (prefs → else Destination.lat/lng) |
| **7.1** | TripService edit ops + schemas + exceptions + private hydrate / day-surgery / persist helpers |
| **7.2** | Four router endpoints + rate-limit path entries |
| **7.3** | `tests/trips/test_edit_replan.py` |
| **7.4** | `EvaluationService.record_edit` + `user_edited` |
| **7.5** | Optional smoke + `docs/context.md` ship update |

Blueprint numbering maps: 7.1≈service, 7.2≈router, 7.3≈tests, 7.4≈evaluation; 7.0/7.5 are contract expansions (same idea as P6.0/6.5).

### D3 — No planner tools on edit path

**Decision:** `TripService` calls pure `travel_engine` (`optimize_route`, `build_day_schedule`, `validate_trip`, rules) and injects `OsrmRoutingProvider` (or test Fake) for `travel_matrix` / `route_polyline`. Never import `PlannerService`, `execute_tool`, or tool impl modules.  
**Rationale:** AGENT Router→Service→Repository; P6 “no PlannerService”; edit is deterministic CRUD surgery, not an agent phase. Blueprint “+ tools” means *same algorithms*, not `TOOL_REGISTRY`.  
**Alternatives:** Call `reoptimize_routes` tool → rejected (ToolContext/TravelState/phase noise). Shared helper extracted from tools → defer until duplication hurts.

### D4 — Base coordinates

**Decision:**
1. **7.0:** `save_from_state` writes `preferences["base_lat"]` / `preferences["base_lng"]` from state (float). No new columns/migration.
2. **Edits:** `_resolve_base(trip, destination) -> (lat,lng)` = prefs base if both present, else `destination.lat/lng`.
3. Document known limitation: trips saved before 7.0 fall back to destination centroid (acceptable for MVP).

**Alternatives:** Always destination → wrong for custom PlanRequest base. New Trip columns → unnecessary migration. Require client to send base on every edit → friction / spoofing.

### D5 — Per-op routing semantics

| Op | Order | Engine |
|----|--------|--------|
| **reorder** | Client `place_ids` must be a **permutation** of that day’s current stops | Fixed-order: matrix for consecutive legs + `build_day_schedule` + leg/day polylines — **do not** call `optimize_route` |
| **remove** | Remaining stops on day | `optimize_route` then schedule + polylines |
| **add** | Append new place then | `optimize_route` then schedule + polylines; validate |
| **reoptimize** | Current day’s places | `optimize_route` then schedule + polylines |

Hydrate each stop → `ScoredPlace` with **score=1.0** and empty breakdown (edit does not re-rank). Category/name/tags/lat/lng from joined `Place` (`to_shape`).

### D6 — Validation and empty day

**Decision:** After mutating the target day in memory, rebuild a full `TripItinerary` from all days (other days hydrated from existing TripPlace timing where possible, or re-derived scores) and run `validate_trip`. If `errors` non-empty → rollback, raise domain error mapped to **422** with `details.validation_warnings` (and errors). Warnings alone do not fail.  
**Empty day:** removing the last stop on a day → **422** (`day_would_be_empty`); do not allow zero-stop days in MVP.  
**Add duplicate:** place already on trip (`uq_trip_place`) → **409** or **422** with clear code (`stop_already_on_trip`); prefer 409 conflict.  
**Add wrong destination:** place.destination_id ≠ trip.destination_id → **422**.  
**Reorder bad set:** not a permutation → **422**.

### D7 — Unit of Work + audit

**Decision:** Single DB transaction per edit: mutate TripPlaces → insert `TripEditEvent` → `record_edit` (flush evaluation flag) → commit. On validation/business failure before commit: rollback; trip unchanged. Payload JSONB = `{ "before": [...], "after": [...] }` stop snapshots (place_id, order, times, polyline).  
`record_edit`: always ensure `TripEditEvent` row exists (service may create event then call evaluation); set `user_edited=True` on latest `TripEvaluation` for `trip_id` if any; if none, still succeed (event-only).

### D8 — Auth and ownership

**Decision:** All four endpoints `require_auth` + ownership (`trip.user_id == user_id`). Guests cannot edit even with matching `wandr_session` — claim first (aligns with P6 “no anonymous destructive”). Soft-deleted / missing → 404. Wrong owner → 403 (not 404).

### D9 — Resilience (edit OSRM)

**Decision:** Same as generation path — `OsrmRoutingProvider` / `geo/osrm` already fail-soft to haversine; `route_polyline` returns `None` on fallback. Edit endpoints return **200** with updated times; polylines may be null. Never 500 on OSRM timeout. No new httpx calls outside `geo/`.

### D10 — HTTP / schemas / rate limits

**Decision:** Return `ApiResponse[TripOut]` with full trip + places after reload (`get_with_places`). Schemas: `ReorderStopsIn`, `AddStopIn` (no body for delete/reoptimize). Path rate limits: e.g. `30/min` per authenticated user (or IP) for `/trips/*/days/*/stops*` and reoptimize — document exact keys in step7; fail-open unchanged.

### D11 — step7.md document structure (locked outline)

Mirror step5/step6:
1. Header (SoT blueprint v6.1 §P7, layering, gate = P6.5 green)
2. Decision / Fix Log (table covering D3–D10)
3. Prerequisites (what’s real vs stub)
4. Prompt conventions + AGENT guardrails reminder
5. P7 architecture ASCII (HTTP → Service → travel_engine + RoutingProvider → UoW)
6. Shared locks: auth matrix, failure table, abstractions, design patterns, code quality rules
7. Steps 7.0–7.5 paste blocks with `─── FAILURE BOUNDARY ───` and ✅
8. Ship criteria + recommended OpenSpec implementation batches

### D12 — Naming: P5 REPLAN vs P7 Edit & Replan

**Decision:** step7.md MUST open with a callout that P7 is **user HTTP day surgery**, not agent `AgentPhase.REPLAN`. Avoid instructing implementers to “call replan tools.”

## Risks / Trade-offs

- [Custom base lost on pre-7.0 trips] → Mitigation: destination fallback; 7.0 persists going forward.
- [Full-trip validate after one-day edit is strict] → Mitigation: correct product; document 422 payload; tests cover overload on add.
- [score=1.0 weakens drop-retry fairness inside optimize_route] → Mitigation: acceptable for edit; user already chose the set; drop-retry rarely triggers on small days.
- [Duplication vs planner reoptimize_routes glue] → Mitigation: accept small duplication; extract later if needed.
- [Agents confuse P5 REPLAN with P7] → Mitigation: D12 callout + Fix Log row.
- [No evaluation row] → Mitigation: TripEditEvent still written; flag optional.

## Migration Plan

1. Apply this change: write `docs/steps/step7.md` + keep OpenSpec deltas; do **not** mark P7 ✅ in `context.md`.
2. Archive/sync when ready; sync capability specs to `openspec/specs/`.
3. Implementation applies (separate): `7.0` → `7.1` → `7.2` → `7.3` → `7.4` → `7.5`.
4. Rollback of planning: restore empty/prior `step7.md` from git; discard change folder.

## Open Questions

- None blocking. Optional later: path-specific rate numbers; extracting shared day-surgery helper used by tools + TripService; persisting dedicated base columns if preferences JSON proves awkward.
