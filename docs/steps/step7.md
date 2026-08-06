# Wandr — P7 Cursor Prompts: Edit & Replan API
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P7 (2 days · 4 blueprint steps, expanded here to **7.0–7.5**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Canonical P7 build contract.** Produced by OpenSpec change `design-p7-edit-replan`.
>
> **Layering (do not confuse):**
> - `docs/blueprint_final.md` = product / architecture source of truth
> - **this file** = Cursor build contract (sub-steps, failure boundaries, ✅ validation, tests)
> - OpenSpec = propose → apply → archive for **batched** implementation clusters
>
> Paste each prompt into Cursor **Agent mode** in order. Do NOT advance until the current
> ✅ validation passes.
>
> Implement **from this prompt only**. Do not invent endpoints, agent replan loops, or LLM
> calls beyond what is locked here.
>
> **Gate:** do not implement P7 code batches until P6.5 is green in `docs/context.md` (or an
> explicitly accepted documented blocker). Do not start code applies until **this** `step7.md`
> exists (planning change `design-p7-edit-replan`).

---

## ⚠ Naming trap — read first

```
P5 AgentPhase.REPLAN  ≠  P7 Edit & Replan HTTP
────────────────────────────────────────────────
Generation-time tools     User mutates a *saved* Trip
(reoptimize_routes, …)    via four day-scoped endpoints
inside LangGraph          — deterministic, no LLM
```

P7 is **day surgery on persisted TripPlaces**. It does **not** enter LangGraph, does **not**
call `execute_tool`, and does **not** use `PlannerService`. Blueprint wording “travel_engine +
tools” means **the same algorithms tools use**, not `TOOL_REGISTRY`.

---

## Decision / Fix Log (read before implementing)

| # | Risk if unlocked | Lock in this prompt |
|---|---|---|
| 1 | Agent confuses P5 REPLAN with P7 HTTP | Callout above; never import planner tools / graph on edit path |
| 2 | `TripService` calls `execute_tool` / `PlannerService` | Edit ops → `travel_engine` + injected `RoutingProvider` only |
| 3 | `Trip` has no base coords → optimize invents origin | **7.0:** persist `base_lat`/`base_lng` on `Trip.preferences`; edits use `_resolve_base` (prefs → else Destination) |
| 4 | Reorder silently TSP-permutes user’s order | Reorder = fixed-order matrix + `build_day_schedule` + polylines — **no** `optimize_route` |
| 5 | Remove/add/reoptimize skip re-route | Those three **do** call `optimize_route` then schedule + polylines |
| 6 | Hydration invents scores / skips Place fields | `ScoredPlace(score=1.0)`; lat/lng via `to_shape`; category/name/`enriched_tags` from Place |
| 7 | Empty day after remove | **422** `day_would_be_empty` — day must keep ≥1 stop |
| 8 | Validation fail still commits | `validate_trip` errors → rollback → **422**; warnings alone OK |
| 9 | OSRM timeout → 500 | Fail-soft haversine / null polyline → **200** (existing provider behavior) |
| 10 | Guest edits via `wandr_session` | All four routes `require_auth` + `trip.user_id == caller`; claim first |
| 11 | Duplicate place / wrong destination on add | Duplicate → **409** `stop_already_on_trip`; wrong dest → **422** |
| 12 | Bad reorder list | Not a permutation of that day’s place_ids → **422** |
| 13 | Edit skips audit / evaluation | Same UoW: TripPlaces + `TripEditEvent` + `record_edit` (`user_edited` if eval row exists) |
| 14 | Exact-match rate limit can’t key UUID paths | P7 edit routes use **global default** rate limit (no fake exact paths); prefix matching = forward lock |
| 15 | LLM / narrative on edit | Forbidden — times/order/geometry from travel_engine + RoutingProvider only |

---

## Prerequisites (P6 must be complete)

Before step 7.0, confirm from `docs/context.md`:

- All P6 steps ✅ — trips HTTP CRUD + GeoJSON + claim; planner SSE; polylines; cache backends
- `python -m pytest tests/ -v` green (202+ when DB up)
- `python scripts/test_p6_smoke.py` green (or documented equivalent)
- **Already real (do NOT reinvent):**
  - `src/trips/models.py` — `Trip`, `TripPlace`, `TripEditEvent`, `EditType`
  - `src/trips/service.py` — `save_from_state`, ownership, claim, `build_geojson` (no PlannerService)
  - `src/trips/router.py` — list/get/delete/geojson/claim
  - `src/trips/schemas.py` — `TripOut`, `TripPlaceOut`
  - `src/planner/routing_provider.py` — `OsrmRoutingProvider` (`travel_matrix` + `route_polyline`)
  - `src/travel_engine/*` — `optimize_route`, `build_day_schedule`, `validate_trip`, protocols, rules
  - `src/evaluation/service.py` — `record_generation` only (`record_edit` = **stub / missing**)
  - Destination model with `lat`/`lng`
- **Still stub / missing for P7:**
  - Edit ops on `TripService`
  - Four edit HTTP routes
  - `EvaluationService.record_edit`
  - `docs/steps/step7.md` was empty before this contract — **you are reading the contract now**

---

## Prompt conventions (every step)

- **Extend, don't replace** P0–P6 code unless the step explicitly says extend.
- **Layering:** Router → Service → Repository only. Router never touches DB or travel_engine.
- **No planner on edit:** never import `PlannerService`, `execute_tool`, `langgraph`, or `src.planner.tools.*` from trips edit code.
- **No LLM on edit:** never call `chat_completion` / `chat_with_tools` from edit path.
- **Travel engine purity:** no network/DB inside `travel_engine/`. Routing only via injected `RoutingProvider`.
- **Geo:** OSRM only through `OsrmRoutingProvider` → `geo/osrm`. No raw httpx in trips.
- **Env:** all via `get_settings()` — never `os.environ.get()`.
- **Responses:** `ApiResponse[TripOut]` for the four edit endpoints — never a raw dict (GeoJSON remains the intentional P6 exception).
- **No new packages** without `requirements.txt` + why-comment. P7 expects **zero** new packages.
- **Failure standards:** every code prompt has `─── FAILURE BOUNDARY ───` and a `✅ Failure path:` line.
- **OpenSpec cadence (implementation):** separate applies `7.0` → `7.1` → `7.2` → `7.3` → `7.4` → `7.5`. Do **not** run full propose→archive for every micro-detail inside a step unless a design conflict appears.
- **Windows:** use `Select-String` instead of `grep` where noted.

---

## P7 architecture (read before implementing)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         P7 dependency graph (canonical order)                │
└──────────────────────────────────────────────────────────────────────────────┘

  7.0 save_from_state persists base_lat/base_lng + _resolve_base helper
        │
  7.1 TripService day surgery (reorder / remove / add / reoptimize_day)
        │     hydrate → travel_engine + RoutingProvider → validate → UoW
        │
  7.2 trips/router.py — four endpoints (require_auth + ownership)
        │
  7.3 tests/trips/test_edit_replan.py
        │
  7.4 EvaluationService.record_edit + user_edited
        │
  7.5 smoke (optional) + docs/context.md
```

```
  HTTP (require_auth)
       │
       ▼
  trips/router.py  ── schemas ReorderStopsIn / AddStopIn
       │
       ▼
  TripService.edit_*  ── assert owner (user_id == trip.user_id)
       │
       ├─► load trip + places + Place (get_with_places)
       ├─► _resolve_base(trip, destination)
       ├─► hydrate TripPlace → ScoredPlace (score=1.0)
       ├─► reorder: travel_matrix (fixed order) + build_day_schedule + route_polyline
       │   remove/add/reoptimize: optimize_route + build_day_schedule (+ polylines inside optimize)
       ├─► rebuild TripItinerary (all days) → validate_trip
       │         errors? → rollback → TripEditValidationError 422
       ├─► mutate TripPlaces + insert TripEditEvent
       ├─► EvaluationService.record_edit(...)  (same UoW)
       └─► commit → reload → TripOut
```

---

## Shared locks (apply to all P7 steps)

### Auth matrix — LOCKED

| Method | Path | Auth |
|--------|------|------|
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | `require_auth` + owner |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | `require_auth` + owner |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | `require_auth` + owner |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | `require_auth` + owner |

Owner = `trip.user_id == payload.user_id`. Unclaimed / guest session alone → **403** (claim first). Soft-deleted / missing → **404**. Wrong owner → **403** (not 404).

Existing P6 routes unchanged.

### Failure-mode table — LOCKED

| Failure | Behavior |
|---------|----------|
| Not authenticated | 401 |
| Not owner / unclaimed | 403 |
| Trip missing / soft-deleted | 404 |
| Reorder not a permutation | 422 |
| Remove last stop on day | 422 `day_would_be_empty` |
| Add place already on trip | 409 `stop_already_on_trip` |
| Add place wrong destination | 422 |
| `validate_trip` errors | 422 + rollback; `details` include errors (+ warnings) |
| `validate_trip` warnings only | 200 OK (commit) |
| OSRM timeout / fallback | 200; times from haversine; polylines may be `None` |
| Partial DB write | Full transaction rollback |

### Abstraction & provider swap — LOCKED

| Concern | Protocol / gateway | Dev | Prod | Swap |
|---------|-------------------|-----|------|------|
| Routing (matrix + polyline) | `RoutingProvider` | Fake in tests | `OsrmRoutingProvider` | ctor / param DI into TripService edit helpers |
| Travel algorithms | pure `travel_engine` | same | same | no I/O |
| Auth | `require_auth` | JWT | JWT | existing |
| Cache / Redis | unchanged | — | — | **not used by P7 edits** |

Trips router MUST NOT `import redis`, `litellm`, or `langgraph`.

### Design patterns — LOCKED

| Module | Pattern | Meaning |
|--------|---------|---------|
| Edit UoW | Unit of Work | TripPlaces + TripEditEvent + eval flag, one commit |
| `RoutingProvider` | Protocol / DI | Same as planner tools; Fake in tests |
| Ownership | Policy / Guard | Auth + `user_id` match (stricter than guest GET) |
| `validate_trip` | Chain of Responsibility | Existing P4 rules — do not fork |
| Router → Service | Service Layer | No DB in router |

### Code quality & system design principles — LOCKED

1. **Single responsibility:** HTTP parsing in router; mutation + routing orchestration in service; flush-only writes in repository.
2. **Determinism:** same inputs + FakeRoutingProvider → same order/times in tests.
3. **Fail closed on business rules** (validation, empty day, ownership); **fail soft on external routing**.
4. **Efficiency:** touch **one day** for matrix/polyline; do not re-run full multi-day agent loop; reorder skips permutations.
5. **Auditability:** every successful edit → `TripEditEvent` with before/after payload.
6. **No speculative abstraction:** do not extract a shared “day surgery” module used by planner tools unless duplication becomes painful (forward lock).
7. **Extend schemas/exceptions in trips domain** — do not overload unrelated modules.

### Forward locks (design-only — do not implement in P7)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | Chat / LLM “replan my whole trip” | post-P7 product |
| F2 | Evaluation HTTP API | later |
| F3 | Rate-limit middleware prefix match for UUID paths | optional hardening |
| F4 | Dedicated `Trip.base_lat` columns (vs preferences JSON) | only if prefs prove awkward |
| F5 | Shared day-surgery helper for tools + TripService | if duplication hurts |

---

## Step 7.0 — Persist base coords + resolve helper

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Generation base coords are on TravelState but not on Trip — edits cannot
honestly re-route without inventing an origin. Persist base into preferences on
save; add a resolve helper for later edit ops. This is step 7.0. No new packages.
No migration. No edit HTTP yet.

─── EXTEND src/trips/service.py — save_from_state ───

  When building the preferences dict for Trip.create, ALSO set:

    preferences["base_lat"] = float(state["base_lat"])   # when present
    preferences["base_lng"] = float(state["base_lng"])   # when present

  Keep existing keys (interests, budget, include_offbeat, include_trekking).
  If base_* missing on state, omit keys (legacy behavior); edits will fall back
  to Destination.

─── ADD helpers on TripService (or module-private functions) ───

  def _resolve_base(trip: Trip, destination) -> tuple[float, float]:
      """
      Prefer trip.preferences base_lat/base_lng when both numeric;
      else destination.lat / destination.lng.
      """
      ...

  Document: trips saved before 7.0 use destination centroid — known MVP limitation.

─── TESTS ───

  Extend existing trips save tests (or add a focused unit test):
  - save_from_state with base_lat/base_lng → preferences contain them
  - _resolve_base prefers prefs over destination when both exist

─── FAILURE BOUNDARY ───

  - Missing base on state → save still succeeds; prefs omit base keys
  - Non-numeric prefs base → treat as missing → destination fallback
  - Never raise 500 from resolve helper

─── DO NOT ───

  - Add DB columns / Alembic migration
  - Change GeoJSON or planner SSE
  - Implement edit endpoints yet
  - Call PlannerService

✅ Validation:
  - Unit test: preferences include base_lat/base_lng after save_from_state
  - Unit test: _resolve_base prefs-win and destination-fallback
  - python -m pytest tests/trips/ -v  (existing + new) green

✅ Failure path: state without base_* → Trip saved; resolve uses Destination.lat/lng
```

---

## Step 7.1 — TripService edit operations

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement day-surgery service methods + schemas + exceptions.
This is step 7.1. No FastAPI routes yet (7.2). Wire RoutingProvider via
constructor default OsrmRoutingProvider() or an optional `routing=` arg for tests.
No new packages. No PlannerService / execute_tool / LLM.

─── EXTEND src/trips/exceptions.py ───

  class TripEditValidationError(WandrError):
      """422 — validation or business rule failed; trip unchanged."""
      def __init__(self, message: str, *, details: dict | None = None):
          super().__init__(
              message,
              code="trip_edit_validation_failed",
              status_code=422,
              details=details or {},
          )

  class TripStopConflictError(WandrError):
      """409 — place already on trip."""
      def __init__(self, message: str = "stop already on trip"):
          super().__init__(
              message,
              code="stop_already_on_trip",
              status_code=409,
          )

  (If WandrError lacks `details=`, extend carefully to match existing ErrorResponse
   mapping used by the app — do not invent a second error envelope.)

─── EXTEND src/trips/schemas.py ───

  class ReorderStopsIn(BaseModel):
      place_ids: list[uuid.UUID]   # full permutation of that day's stops

  class AddStopIn(BaseModel):
      place_id: uuid.UUID

─── EXTEND src/trips/repository.py (as needed) ───

  Flush-only helpers if missing, e.g.:
  - delete TripPlace by id / (trip_id, place_id, day)
  - update order/times/polyline fields on existing rows
  - insert TripEditEvent
  Keep soft-delete rules: TripPlace is hard-deleted (no SoftDeleteMixin).

─── EXTEND src/trips/service.py — private helpers ───

  _hydrate_scored(trip_place) -> ScoredPlace
    PlaceCandidate from joined Place (to_shape → lat/lng; category; name;
    enriched_tags list). score=1.0, score_breakdown={}.

  _snapshot_day(places_for_day) -> list[dict]
    {place_id, order_in_day, travel_time_min, visit_duration_min,
     suggested_start_time, polyline} for edit payload.

  async def _fixed_order_day(scored_in_order, base_lat, base_lng, routing)
    -> (ordered, legs, leg_polylines)
    # Build waypoints [BASE_SENTINEL + stops]; travel_matrix once;
    # consecutive legs for that order; route_polyline per leg (same pattern as
    # optimize_route's _populate_polylines). Do NOT permute.

  async def _optimize_day(scored, base_lat, base_lng, routing) -> OptimizeResult
    # thin wrapper: await optimize_route(...)

  def _day_plan_from_result(...) -> DayPlan
    # build_day_schedule(ordered, legs) → DayPlan(stops=..., total_travel_min=...,
    # dropped_stops=...)

  async def _validate_full_trip(trip, mutated_day_number, new_day_plan) -> None
    # Build TripItinerary for ALL days: mutated day uses new_day_plan;
    # other days hydrated from existing TripPlaces → ScheduledStop-compatible
    # structures (reuse hydrate + reconstruct DayPlan with stored travel totals
    # if available, or recompute lightly). Call validate_trip.
    # On errors: raise TripEditValidationError(details={
    #   "validation_errors": result.errors,
    #   "validation_warnings": result.warnings,
    # })

  async def _persist_day_and_audit(...)
    # Apply TripPlace mutations for the day; insert TripEditEvent;
    # call EvaluationService.record_edit (7.4 may stub no-op until then —
    # if 7.4 not applied yet, insert TripEditEvent here and leave a TODO hook
    # OR implement record_edit in 7.1 as thin event+flag and let 7.4 deepen tests.
    # Preferred: 7.1 inserts TripEditEvent in UoW; calls record_edit if available;
    # 7.4 makes record_edit real and sets user_edited.)
    # commit; return get_with_places.

─── PUBLIC METHODS ───

  async def reorder_stops(self, trip_id, day, place_ids, user_id, *, routing=None) -> Trip
  async def remove_stop(self, trip_id, day, place_id, user_id, *, routing=None) -> Trip
  async def add_stop(self, trip_id, day, place_id, user_id, *, routing=None) -> Trip
  async def reoptimize_day(self, trip_id, day, user_id, *, routing=None) -> Trip

  Common preamble:
    - load trip with places (404 if missing)
    - if trip.user_id != user_id: raise TripForbiddenError
    - resolve destination; base = _resolve_base(...)
    - filter places for day_number == day; 422 if day has no stops (except add
      onto empty day is allowed only if product wants it — LOCKED: add onto a day
      that currently has zero stops is allowed; remove that would empty is not)

  reorder_stops:
    - require sorted(place_ids) == sorted(current day place_ids) as sets and
      same length (permutation); else TripEditValidationError
    - order scored list by place_ids
    - _fixed_order_day → schedule → validate full trip → persist
    - EditType.REORDER; payload before/after

  remove_stop:
    - if place not on that day → 404 or 422 (prefer 404 TripNotFound-style for stop)
    - if len(day_stops)==1 → TripEditValidationError code day_would_be_empty
    - remaining → optimize_route → schedule → validate → persist
    - EditType.REMOVE_STOP; place_id set

  add_stop:
    - load Place; if missing → 404
    - if place.destination_id != trip.destination_id → 422
    - if place_id already on trip (any day) → TripStopConflictError 409
    - append hydrated place to day scored list → optimize_route → schedule →
      validate → persist (insert new TripPlace)
    - EditType.ADD_STOP

  reoptimize_day:
    - current day scored → optimize_route → schedule → validate → persist
    - EditType.REOPTIMIZE_DAY

─── FAILURE BOUNDARY ───

  - validate_trip.errors → rollback, TripEditValidationError 422
  - OSRM fail → provider fallback; still 200 path at HTTP layer (service returns Trip)
  - Never leave half-updated day committed
  - Never call LLM / PlannerService / execute_tool

─── DO NOT ───

  - Register routes (7.2)
  - Cross-day move endpoints
  - Chat replan
  - New tables

✅ Validation:
  - from src.trips.service import TripService
  - methods reorder_stops, remove_stop, add_stop, reoptimize_day exist
  - python -c "import ast; ..." or pytest unit with FakeRoutingProvider:
      reorder preserves order; remove last → error; add duplicate → 409

✅ Failure path: injected validation failure → session rolled back; no TripEditEvent row
```

---

## Step 7.2 — trips/router.py edit endpoints

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Expose the four blueprint edit endpoints. This is step 7.2.
Reuse TripService from 7.1. Return ApiResponse[TripOut]. No new packages.

─── EXTEND src/trips/router.py ───

  PATCH /{trip_id}/days/{day}/stops/reorder
    body: ReorderStopsIn
    Depends(require_auth)
    → ApiResponse[TripOut]

  DELETE /{trip_id}/days/{day}/stops/{place_id}
    Depends(require_auth)
    → ApiResponse[TripOut]

  POST /{trip_id}/days/{day}/stops
    body: AddStopIn
    Depends(require_auth)
    → ApiResponse[TripOut]

  POST /{trip_id}/days/{day}/reoptimize
    Depends(require_auth)
    → ApiResponse[TripOut]

  day: int path param (1-based day_number as stored on TripPlace).
  Pass payload.user_id into service. Map domain errors via existing exception handlers.

─── RATE LIMITS ───

  Do NOT add broken exact-match UUID paths to _route_limit_table.
  Edit routes inherit RATE_LIMIT_DEFAULT_* (document in context on 7.5).
  Prefix matching is forward lock F3.

─── FAILURE BOUNDARY ───

  - Unauthenticated → 401
  - Non-owner → 403
  - Service validation → 422 ErrorResponse
  - Conflict → 409
  - Router performs no DB / no travel_engine imports

─── DO NOT ───

  - optional_auth on edits
  - Return raw dict
  - Import redis / litellm

✅ Validation:
  - OpenAPI /docs lists four new routes
  - Manual or test client: owner reorder day 1 → 200 TripOut; times/polyline updated
  - GET /trips/{id}/geojson reflects new geometry when polylines present
  - Guest/unauth → 401; other user → 403

✅ Failure path: add stop that overloads day → 422; DB trip unchanged (re-GET matches pre-edit)
```

---

## Step 7.3 — tests/trips/test_edit_replan.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Pytest coverage for P7 edit/replan. This is step 7.3.
Use FakeRoutingProvider from travel_engine tests (deterministic matrix + polyline).
Prefer service-level tests + a thin HTTP test for auth matrix.

─── CREATE tests/trips/test_edit_replan.py ───

  Required scenarios:
  1. reorder — order_in_day matches client permutation; suggested_start_time updated
  2. remove_stop — stop gone; remaining re-routed
  3. remove last stop on day — 422 / TripEditValidationError; unchanged
  4. add_stop — new TripPlace; optimize ran
  5. add duplicate place — 409
  6. add wrong destination — 422
  7. reoptimize_day — succeeds with Fake routing
  8. ownership — wrong user_id → TripForbiddenError / HTTP 403
  9. OSRM fallback — Fake that returns fallback / None polyline → still success (no 500)
 10. validation failure — force over-cap or mock validate_trip errors → rollback;
     no TripEditEvent committed
 11. successful edit → TripEditEvent row with correct EditType + payload before/after

─── FAILURE BOUNDARY ───

  Tests must not require live OSRM or LLM.
  DB: use wandr_test / existing fixtures pattern from tests/trips/.

─── DO NOT ───

  - Hit real OSRM in CI unit tests
  - Skip ownership or rollback cases

✅ Validation:
  python -m pytest tests/trips/test_edit_replan.py -v  → green
  Full suite still green: python -m pytest tests/ -v

✅ Failure path: test asserts rollback — count TripEditEvent before/after failed add
```

---

## Step 7.4 — EvaluationService.record_edit + user_edited

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Honor AGENT.md — evaluation records every edit. This is step 7.4.

─── EXTEND src/evaluation/repository.py ───

  async def get_latest_for_trip(self, trip_id: UUID) -> TripEvaluation | None
  async def mark_user_edited(self, evaluation: TripEvaluation) -> TripEvaluation
    # set user_edited=True; flush only

─── EXTEND src/evaluation/service.py ───

  async def record_edit(
      self,
      trip_id: UUID,
      edit_type: EditType | str,
      *,
      day_number: int | None = None,
      place_id: UUID | None = None,
      payload: dict | None = None,
  ) -> TripEditEvent:
      """
      LOCKED pattern: create TripEditEvent (flush) THEN set user_edited on latest
      TripEvaluation for trip_id if one exists. If no evaluation, still return the
      event (edit succeeds). No LLM. No planner.
      """
      # If TripService already inserted the event in 7.1, prefer ONE owner:
      # Option A (LOCKED): EvaluationService.record_edit creates the TripEditEvent;
      #   TripService calls record_edit and does not insert the event itself.
      # Use Option A to avoid double rows — refactor 7.1 hook accordingly if needed.

─── WIRE TripService ───

  After successful in-memory mutation + validate, call record_edit inside the
  same session before commit (UoW).

─── FAILURE BOUNDARY ───

  - No evaluation row → event only; no exception
  - Prefer including event+flag in same transaction as place mutations
  - Do not convert a successful edit into 500 because flag update failed —
    keep flag update in-UoW so rollback covers it; avoid post-commit best-effort
    unless you log and swallow (prefer in-UoW)

─── DO NOT ───

  - New TripEvaluation columns / migrations
  - Evaluation HTTP routes
  - Skip TripEditEvent on success

✅ Validation:
  - Edit trip with existing evaluation → user_edited is True
  - Edit trip without evaluation → TripEditEvent exists; HTTP 200
  - Four edit types produce four EditType values across tests

✅ Failure path: missing evaluation does not block edit
```

---

## Step 7.5 — Smoke + context.md ship

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Close P7 documentation checkpoint. Optional live smoke. This is step 7.5.
Only mark context.md after pytest (and smoke if present) are green.

─── OPTIONAL scripts/test_p7_smoke.py ───

  If written: seed or use existing trip owned by a test user; reorder day 1;
  assert TripEditEvent; print GeoJSON snippet. Keep offline-capable with Fake
  where possible; live OSRM optional behind env flag (same spirit as P4/P6).

─── UPDATE docs/context.md ───

  - Last updated = today; Next step = post-P7 / production readiness (per blueprint)
  - Progress: 7.0–7.5 ✅
  - Current state one-liner: P7 done — trip day edit/replan HTTP + TripEditEvent
  - Implemented modules: edit methods, routes, record_edit
  - Live endpoints: four edit rows
  - Stubs only: remove “P7 trip edit/replan HTTP still stubs”
  - Do NOT claim evaluation HTTP done

─── IMPORT GUARDS ───

  Spot-check: trips edit modules do not import litellm, langgraph, PlannerService,
  execute_tool, redis.

─── FAILURE BOUNDARY ───

  - Do not update context.md if tests fail
  - Smoke must not require production secrets beyond existing .env patterns

─── DO NOT ───

  - Start F1 chat replan
  - Mark roadmap production items done

✅ Validation:
  - python -m pytest tests/trips/test_edit_replan.py -v
  - python -m pytest tests/ -v
  - (optional) python scripts/test_p7_smoke.py
  - context.md Next step advanced; P7 rows ✅

✅ Failure path: failed pytest → context.md unchanged
```

---

## P7 ship criteria

| Check | Expected |
|-------|----------|
| Base prefs | `save_from_state` stores `base_lat`/`base_lng` when present on state |
| Resolve base | prefs win; else Destination |
| Reorder | User order preserved; times + polylines refreshed; no TSP |
| Remove / add / reoptimize | `optimize_route` path; TripOut returned |
| Empty day | 422; unchanged |
| Validation errors | 422 + rollback; no audit row |
| OSRM fallback | 200 not 500 |
| Auth | require_auth; non-owner 403; guest cannot edit |
| Audit | TripEditEvent per success; `user_edited` when eval exists |
| Layering | No PlannerService / execute_tool / LLM / litellm / langgraph on edit path |
| Envelope | `ApiResponse[TripOut]` |
| GeoJSON | Reflects post-edit polylines without new endpoint |
| pytest | `test_edit_replan` + full suite green |
| context.md | Updated only on 7.5 after green |

---

## Recommended OpenSpec implementation batches

Code implementation is **not** part of the `design-p7-edit-replan` planning change
(that change only authors this file + specs).

After P6.5 is green **and** this `docs/steps/step7.md` exists, apply these as
**separate** OpenSpec implementation changes (or batched `/opsx:apply` sessions), in order:

1. `7.0` — base coords on preferences + `_resolve_base`
2. `7.1` — TripService edit ops + schemas + exceptions
3. `7.2` — four router endpoints
4. `7.3` — `tests/trips/test_edit_replan.py`
5. `7.4` — `EvaluationService.record_edit` + `user_edited` (reconcile event ownership with 7.1)
6. `7.5` — smoke (optional) + `docs/context.md`

Do **not** open a full propose→archive cycle for each micro-detail inside a step unless a
design conflict appears. Sync delta specs from `design-p7-edit-replan`
(`p7-trip-edit-replan`, `p7-edit-evaluation`, `trips-repository-service`) to main via
`/opsx:sync` or archive workflow when that planning change is archived — do **not**
hand-edit `openspec/specs/` outside that workflow.
