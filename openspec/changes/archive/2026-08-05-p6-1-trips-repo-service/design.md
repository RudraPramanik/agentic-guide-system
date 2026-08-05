## Context

P5 ships `PlannerService.generate` (HTTP-agnostic). P6.0 threads road geometry into `TravelState.schedule` day dicts (`leg_polyline` / `day_polyline`). Trip / TripPlace / TripEditEvent **models** exist (P1); `src/trips/{repository,service,schemas,exceptions,router}.py` remain ~1-line stubs. AuthService precedent: repository flush-only, service owns `commit`. No SQLAlchemy `relationship()` exists anywhere yet — `get_with_places` needs an explicit eager-load strategy.

Step contract: `docs/steps/step6.md` §6.1. SoT locks: `docs/blueprint_final.md` v6.1 (UoW save, guest ownership 403, anonymous claim). AGENT.md: Router → Service → Repository; no PlannerService from trips; no litellm/geo in trips.

**Prerequisite gate (verified this propose):** context Next → P6.1; P5.1–5.14 ✅; `route_polyline` / schedule polylines present; models real; trips HTTP still stub.

## Goals / Non-Goals

**Goals:**

- Real `TripRepository` + `TripService` with locked `save_from_state` field map (incl. `polyline` ← `leg_polyline`).
- Ownership helper `assert_can_access` (403 never 404 on miss-ownership).
- Restored `claim_for_user` (409 already-claimed, 403 session mismatch).
- `TripOut` / `TripPlaceOut` schemas ready for 6.3 router (lat/lng via joined Place + `to_shape`).
- Unit-testable with `AsyncSession` directly; import-surface ✅ validation from step6.md.

**Non-Goals:**

- Registering `trips/router` or any HTTP endpoint (6.3).
- Planner SSE / `PlanRequest` / Redis / cache (6.2 / 6.4).
- `build_geojson` (6.3) — though schemas must expose fields GeoJSON will need.
- Persisting `day_polyline` as its own column (not in `TripPlace` model; 6.3 reconstructs LineStrings from per-stop polylines and/or concatenates as needed).
- P7 edit/replan ops; evaluation coupling from trips service.
- Marking P6 complete in `docs/context.md` (only Progress 6.1 after green apply).

## Decisions

### D1 — Commit boundary matches AuthService

**Choice:** Repository methods flush only (`BaseRepository.create` / add+flush). `TripService.save_from_state` and `claim_for_user` call `await self.session.commit()` (and refresh) on success; on any failure during save, `await self.session.rollback()` so no orphan Trip remains.

**Alternatives:** Commit in repository — rejected (breaks AuthService precedent and UoW composition). Nested savepoints only — rejected as unnecessary for single-trip save.

### D2 — `save_from_state` → `Trip | None` (not always Trip)

**Choice (LOCKED from step6 v2):** Return `None` when there is nothing usable to persist: empty `state["schedule"]`, or clarification-only / incomplete generation (`plan_complete` false and `abort_triggered` false with no usable schedule). Evaluation continues to be written by planner/evaluation path independently.

**Status mapping (LOCKED):**

| Condition | `Trip.status` |
|-----------|---------------|
| `plan_complete` and not `abort_triggered` | `COMPLETE` |
| `abort_triggered` | `FAILED` |
| else (partial but schedule present) | `DRAFT` |

**Field map (LOCKED):** as step6 Decision Log / Trip save UoW block — preferences JSON from interests/budget/include_*; each stop → `TripPlace` with `polyline=stop.get("leg_polyline")`. Parse `place_id` / `destination_id` to `UUID`. Do not invent columns.

### D3 — Ownership policy (pre-HTTP)

**Choice:** `assert_can_access(trip, *, user_id, session_id) -> None`:

- Guest (`user_id is None`): require `session_id == trip.session_id`, else `TripForbiddenError`.
- Authenticated: allow if `trip.user_id == user_id`, **or** (`trip.user_id is None` and `session_id == trip.session_id`) so the original guest session can still read pre-claim.
- Missing trip is **not** this helper’s job — callers use `get_with_places` / `get_by_id` → `TripNotFoundError` (404). Ownership miss is always 403.

**Claim:** `claim_for_user`: `trip.user_id is None` else `TripAlreadyClaimedError` (409); session must match else `TripForbiddenError`; then set `user_id`, commit, return trip.

### D4 — Eager load via new relationships (no migration)

**Choice:** Add SQLAlchemy 2.0 `relationship()` only (no new columns/Alembic):

- `Trip.places` → `list[TripPlace]` ordered by `(day_number, order_in_day)`
- `TripPlace.place` → `Place`
- Optional `Place` back-populates if needed for typing

`get_with_places` uses `selectinload(Trip.places).selectinload(TripPlace.place)` (or equivalent) and soft-delete filter on Trip.

**Alternatives:** Raw join queries without relationships — workable but repeats join logic for every consumer (GeoJSON, schemas). Rejected for maintainability.

### D5 — Schemas: lat/lng from Place geometry; no invented fields

**Choice:** `TripPlaceOut` includes model columns plus `lat`/`lng` (and `name` only if already available from joined Place without inventing DB columns — prefer include `name` from Place for 6.3 UX; it is Place data, not a new TripPlace column). Build via factory/`model_validate` + `geoalchemy2.shape.to_shape` (same pattern as `PlaceOut.from_place`). `TripOut` nests places list + trip scalar fields (`id`, `destination_id`, `days`, `preferences`, `status`, `user_id`, `session_id`, timestamps).

### D6 — Exceptions inherit core hierarchy

**Choice:**

- `TripNotFoundError(NotFoundError)` — code/message trip-specific
- `TripForbiddenError(ForbiddenError)`
- `TripAlreadyClaimedError(WandrError)` with `status_code=409`, `code="trip_already_claimed"` (no `ConflictError` base exists yet; domain exception is enough for 6.1)

Global WandrError handler already maps `status_code` — no router try/except needed in 6.3.

### D7 — Tests cadence

**Choice:** This apply MUST pass step6.md import-surface validation. Prefer also landing **focused** `tests/trips/` for UoW rollback + claim 403/409 in this change (hardening vs deferring everything to 6.5) — keep GeoJSON/HTTP tests for 6.3/6.5. Do not block 6.1 on full P6 smoke.

### D8 — `day_polyline` not stored

**Choice:** Only per-stop `leg_polyline` → `TripPlace.polyline`. Aggregate `day_polyline` remains schedule/SSE display data until/unless a later column is proposed. GeoJSON (6.3) builds LineStrings from per-stop polylines (decode/concat or one LineString per leg) — documented so implementers do not invent a `trips.day_polyline` column in 6.1.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `UniqueConstraint(trip_id, place_id)` rejects same place on two days | Known P1 model lock; do not alter in 6.1. If agent schedules a revisit, save fails → rollback → surface as 500/integrity until product revisits constraint (open question). |
| Missing Place FK on insert | IntegrityError → rollback; never orphan Trip. Callers (6.2) only save schedules whose place_ids came from DB. |
| Guest claim race (two users) | Second claim → 409; first wins. Acceptable for MVP. |
| Relationships unused elsewhere | Additive only; no migration; low risk. |
| Uncommitted P6.0 tree in working copy | Commit/archive hygiene before or with 6.1 apply so Next-step stamps stay honest. |
| Orphan `openspec/changes/p6-0-route-geometry-polyline` after archive | Delete leftover folder or re-archive cleanup so `openspec list` stays accurate. |

## Migration Plan

1. Implement exceptions → schemas → model relationships → repository → service.
2. Run step ✅ import validation; run focused trips unit tests if added.
3. Update `docs/context.md`: Progress 6.1 ✅, Next → P6.2; add trips repo/service to Implemented modules; keep router/planner HTTP as stubs.
4. No Alembic migration expected (relationships only).
5. Rollback: revert trips stub files + relationship lines; no DB downgrade.

## Open Questions

1. **Same-place multi-day uniqueness** — leave as-is for 6.1, or schedule a tiny follow-up migration to `UniqueConstraint(trip_id, day_number, place_id)` / drop uniqueness? Recommendation: leave for now; track if smoke hits IntegrityError on real itineraries.
2. **Minimal 6.1 pytest now vs 6.5 only** — recommendation: land UoW + claim unit tests in 6.1 (step text says “land with 6.5” as the full suite home, not a ban on earlier tests).
3. **`ConflictError` in `src/core/exceptions.py`** — optional shared base for 409; not required if domain exception sets `status_code=409`.
