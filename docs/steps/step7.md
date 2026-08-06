# Wandr — P7 Cursor Prompts: Edit & Replan API (v2.1 — hardened)
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P7 (2 days · 4 blueprint steps, expanded here to **7.0–7.6**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Canonical P7 build contract (single SoT for implementation).** Produced by OpenSpec change
> `harden-p7-step7-prompt` (supersedes v1 from `design-p7-edit-replan`). Historical review notes:
> [`docs/step7_critics.md`](../step7_critics.md) — **not** the build contract.
>
> **v2.1 changelog (vs v1):** resolves TripEditEvent ownership contradiction; shares polyline
> population without collapsing `OptimizeResult.legs` to consecutive-only; persists polylines via
> parallel `leg_polylines` → `TripPlace.polyline` (no invented DayPlan/ScheduledStop fields);
> rejects silent `dropped_stops` on add/reoptimize; locks zero-network unchanged days; locks
> **preserve-order** schedule for reorder + morning-slot warning downgrade; precise permutation /
> 404 / user-keyed rate limit; documents concurrency last-write-wins.
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
> calls beyond what is locked here. During code applies, replan only when feature reality
> conflicts with a lock — amend **this file** first, then code (minimal delta).
>
> **Gate:** do not implement P7 code batches until P6.5 is green in `docs/context.md`,
> `RoutingProvider.route_polyline()` is real (P6.0), and generation persists polylines end-to-end.
>
> **Blueprint deltas (intentional, locked here):**
> - Evaluation does **not** create `TripEditEvent` (TripService does); evaluation only sets `user_edited`
> - DELETE / add / reoptimize use `travel_engine` + `RoutingProvider`, **not** `build_route` / TOOL_REGISTRY
> - Reorder uses preserve-order schedule (generation morning-extract unchanged)

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
| 4 | Reorder silently TSP-permutes user’s order | Reorder = fixed-order matrix + consecutive legs + shared polyline helper — **no** `optimize_route` |
| 5 | Remove/add/reoptimize skip re-route | Those three **do** call `optimize_route` (winning order uses same polyline helper) |
| 6 | Hydration invents scores / skips Place fields | `ScoredPlace(score=1.0)`; lat/lng via `to_shape`; category/name/`enriched_tags` from Place |
| 7 | Empty day after remove | **422** `day_would_be_empty` — day must keep ≥1 stop |
| 8 | Validation fail still commits | `validate_trip` errors → rollback → **422**; warnings alone OK |
| 9 | OSRM timeout → 500 | Fail-soft haversine / null polyline → **200** (existing provider behavior) |
| 10 | Guest edits via `wandr_session` | All four routes `require_auth` + `trip.user_id == caller`; claim first |
| 11 | Duplicate place / wrong destination on add | Duplicate → **409** `stop_already_on_trip`; wrong dest → **422** |
| 12 | Bad reorder list | Not exact permutation (`len` equal **and** `set` equal) → **422** |
| 13 | Edit skips audit / evaluation | Same UoW: TripPlaces + `TripEditEvent` (TripService) + `mark_trip_edited` (flag only) |
| 14 | Edit routes unrate-limited vs OSRM cost | User-keyed `rate_limit_trip_edit` dependency (not UUID path-table hacks) |
| 15 | LLM / narrative on edit | Forbidden — times/order/geometry from travel_engine + RoutingProvider only |
| 16 ★ | **v1 self-contradiction:** 7.1 vs 7.4 disagreed on who creates `TripEditEvent` | **TripService** creates event; `EvaluationService.mark_trip_edited` is flag-only |
| 17 ★ | Duplicate polyline loops → drift; naive “shared legs helper” collapses full matrix | Promote shared **polyline** helper; `OptimizeResult.legs` stays **full pairwise** matrix |
| 18 ★ | Inventing `ScheduledStop.leg_polyline` / `DayPlan.day_polyline` | Keep `leg_polylines` parallel; zip → `TripPlace.polyline` at persist |
| 19 ★ | `add_stop`/`reoptimize` silently drop another stop via optimize drop-retry | Non-empty `dropped_stops` → **422** `edit_would_drop_other_stops` + rollback |
| 20 ★ | “Other days recompute lightly” → accidental multi-day OSRM | Unchanged days from stored TripPlace fields only — **zero** extra network |
| 21 ★ | `build_day_schedule` morning-extract defeats reorder | REORDER uses **preserve-order** schedule; morning-slot errors → warnings on reorder only |
| 22 ★ | Concurrent edits undocumented | MVP limitation: last-write-wins, no row locking |

★ = hardened in v2.1 (critics + verification).

---

## Prerequisites (P6 must be complete)

Before step 7.0, confirm from `docs/context.md`:

- All P6 steps ✅ — trips HTTP CRUD + GeoJSON + claim; planner SSE; **`route_polyline` real**; cache backends
- `python -m pytest tests/ -v` green
- `python scripts/test_p6_smoke.py` green (or documented equivalent)
- **Already real (do NOT reinvent):**
  - `src/trips/models.py` — `Trip`, `TripPlace`, `TripEditEvent`, `EditType`
  - `src/trips/service.py` — `save_from_state`, ownership, `claim_for_user`, `build_geojson`
  - `src/trips/router.py` — list/get/delete/geojson/claim
  - `src/trips/schemas.py` — `TripOut`, `TripPlaceOut`
  - `src/planner/routing_provider.py` — `OsrmRoutingProvider` (`travel_matrix` + `route_polyline`)
  - `src/travel_engine/*` — `optimize_route` (full pairwise legs + `_populate_polylines`), `build_day_schedule` (morning extract), `validate_trip`
  - `src/evaluation/service.py` — `record_generation` only
  - Destination model with `lat`/`lng`
- **Still stub / missing for P7:**
  - Shared public polyline helper (7.1 promotes existing private logic)
  - Preserve-order schedule entry (7.2 / schedule_builder)
  - Edit ops on `TripService` + four HTTP routes + rate limit
  - `EvaluationService.mark_trip_edited`

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
- **OpenSpec cadence:** separate applies `7.0` → `7.1` → `7.2` → `7.3` → `7.4` → `7.5` → `7.6`.
- **Windows:** use `Select-String` instead of `grep` where noted.

---

## P7 architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         P7 dependency graph (canonical order)                │
└──────────────────────────────────────────────────────────────────────────────┘

  7.0 save_from_state persists base_lat/base_lng + _resolve_base helper
        │
  7.1 travel_engine — promote shared polyline helper; optimize_route keeps full matrix legs
        │
  7.2 TripService day surgery + preserve-order schedule path
        │     hydrate → travel_engine + RoutingProvider → validate → UoW
        │     TripService creates TripEditEvent; mark_trip_edited flag-only
        │
  7.3 trips/router.py — four endpoints (require_auth + ownership + user-keyed rate limit)
        │
  7.4 tests/trips/test_edit_replan.py
        │
  7.5 EvaluationService.mark_trip_edited (narrow — flag only)
        │
  7.6 smoke (optional) + docs/context.md
```

```
  HTTP (require_auth + rate_limit_trip_edit)
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
       ├─► reorder: fixed-order matrix + consecutive legs + shared polyline helper
       │         + build_day_schedule_preserve_order (NO morning extract)
       │   remove/add/reoptimize: optimize_route → schedule (default morning extract OK)
       ├─► if optimize_route returned dropped_stops → 422, rollback
       ├─► rebuild TripItinerary: mutated day = new plan; OTHER days from stored TripPlaces
       │         (zero new network calls)
       ├─► validate_trip; REORDER only: downgrade morning_slot_violation* → warnings
       │         remaining errors? → rollback → TripEditValidationError 422
       ├─► mutate TripPlaces (zip leg_polylines → polyline) + insert TripEditEvent
       ├─► EvaluationService.mark_trip_edited(trip_id)  (flag only, same UoW)
       └─► commit → reload → TripOut
```

---

## Shared locks (apply to all P7 steps)

### Auth matrix — LOCKED

| Method | Path | Auth |
|--------|------|------|
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | `require_auth` + owner + `rate_limit_trip_edit` |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | `require_auth` + owner + `rate_limit_trip_edit` |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | `require_auth` + owner + `rate_limit_trip_edit` |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | `require_auth` + owner + `rate_limit_trip_edit` |

Owner = `trip.user_id == payload.user_id`. Unclaimed / guest session alone → **403** (claim first). Soft-deleted / missing → **404**. Wrong owner → **403** (not 404).

Existing P6 routes unchanged.

### Failure-mode table — LOCKED (v2.1)

| Failure | Behavior |
|---------|----------|
| Not authenticated | 401 |
| Not owner / unclaimed | 403 |
| Trip missing / soft-deleted | 404 |
| Reorder not exact permutation (`len` + `set`) | 422 |
| Stop not on that day (`remove_stop`) | **404** `stop_not_found_on_day` |
| Remove last stop on day | 422 `day_would_be_empty` |
| Add place already on trip | 409 `stop_already_on_trip` |
| Add place wrong destination | 422 |
| `optimize_route` non-empty `dropped_stops` (add/reoptimize) | **422** `edit_would_drop_other_stops` |
| `validate_trip` errors (after any reorder morning downgrade) | 422 + rollback |
| Reorder morning-slot errors only | Downgraded to warnings; **200** commit |
| `validate_trip` warnings only | 200 OK (commit) |
| OSRM timeout / fallback | 200; times from haversine; polylines may be `None` |
| Partial DB write | Full transaction rollback |
| Edit rate limit exceeded | 429 |
| Concurrent edits same trip | **MVP:** last-write-wins (no row locking) |

### Abstraction & provider swap — LOCKED

| Concern | Protocol / gateway | Dev | Prod | Swap |
|---------|-------------------|-----|------|------|
| Routing (matrix + polyline) | `RoutingProvider` | Fake in tests | `OsrmRoutingProvider` | ctor / param DI |
| Polyline population | shared helper in `route_optimizer` | Fake | Osrm | same fn |
| Travel algorithms | pure `travel_engine` | same | same | no I/O |
| Auth | `require_auth` | JWT | JWT | existing |
| Edit rate limit | `RateLimiterBackend` | in-memory | Redis if configured | `get_rate_limiter()`, key by `user_id` |
| Cache / Redis | unchanged | — | — | **not used by P7 edit logic** (limiter may share Redis) |

Trips router MUST NOT `import redis`, `litellm`, or `langgraph`.

### Design patterns — LOCKED

| Module | Pattern | Meaning |
|--------|---------|---------|
| Edit UoW | Unit of Work | TripPlaces + TripEditEvent + eval flag, one commit |
| `RoutingProvider` | Protocol / DI | Same as planner tools; Fake in tests |
| Shared polyline helper | Extract Method | Single source for order → polylines; optimize keeps full matrix legs |
| Preserve-order schedule | Parameter / twin fn | Reorder does not run morning extract |
| Ownership | Policy / Guard | Auth + `user_id` match |
| `validate_trip` | Chain of Responsibility | Existing P4 rules; reorder downgrade in TripService only |
| Router → Service | Service Layer | No DB in router |

### Code quality & system design principles — LOCKED

1. **Single responsibility:** HTTP in router; mutation + routing orchestration in service; flush-only writes in repository.
2. **Determinism:** same inputs + FakeRoutingProvider → same order/times/polylines in tests.
3. **Fail closed on business rules** (validation, empty day, ownership, unrequested drops); **fail soft on external routing**.
4. **Efficiency:** touch **one day** for matrix/polyline; unchanged days = zero extra network; reorder skips permutations.
5. **Auditability:** exactly one `TripEditEvent` per success, created by trips domain.
6. **No silent side-effects:** never drop a stop the caller did not ask to remove.
7. **No speculative model invention:** do not add polyline fields to `ScheduledStop`/`DayPlan` in P7.
8. **No speculative abstraction beyond proven callers:** share polyline helper; do not extract a full “day surgery” module until a third caller hurts (forward lock F5).

### Forward locks (design-only — do not implement in P7)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | Chat / LLM “replan my whole trip” | post-P7 product |
| F2 | Evaluation HTTP API | later |
| F3 | Row-level locking for concurrent edits | if multi-device editing is real |
| F4 | Dedicated `Trip.base_lat` columns (vs preferences JSON) | only if prefs prove awkward |
| F5 | Shared day-surgery helper beyond polyline / preserve-order schedule | if duplication hurts |

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
      prefs = trip.preferences or {}
      lat, lng = prefs.get("base_lat"), prefs.get("base_lng")
      if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
          return float(lat), float(lng)
      return destination.lat, destination.lng

  Document: trips saved before 7.0 use destination centroid — known MVP limitation.

─── TESTS ───

  Extend existing trips save tests (or add a focused unit test):
  - save_from_state with base_lat/base_lng → preferences contain them
  - _resolve_base prefers prefs over destination when both exist
  - _resolve_base falls back to destination when prefs base is missing or non-numeric

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

## Step 7.1 — Shared polyline helper (safe extract)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Promote the existing private polyline loop so generation and P7 reorder share one
implementation — WITHOUT changing OptimizeResult.legs semantics. This is step 7.1.
No new packages. Touches src/travel_engine/route_optimizer.py only.

─── EXTEND src/travel_engine/route_optimizer.py ───

  Promote `_populate_polylines` to a public (or module-documented) helper, e.g.:

  async def populate_leg_polylines(
      ordered: list[ScoredPlace],
      base_lat: float,
      base_lng: float,
      routing: RoutingProvider,
  ) -> tuple[list[str | None], str | None]:
      """
      Given an ALREADY-DECIDED order (no permutation search), compute:
        - leg_polylines: aligned to ordered; index i = polyline INTO ordered[i]
        - day_polyline: aggregate for base + all stops
      Called by:
        1. optimize_route() after winning order is final
        2. TripService reorder fixed-order path (step 7.2)
      MUST NOT change OptimizeResult.legs — that remains the full pairwise matrix.
      """

  Refactor optimize_route to call populate_leg_polylines (behavior-preserving).
  OptimizeResult.legs MUST remain list(matrix) / full pairwise — schedule morning
  extract on non-reorder paths needs arbitrary hop lookups.

─── OPTIONAL thin fixed-order helper (same module or TripService in 7.2) ───

  If useful, add compute_fixed_order_legs(...) that:
    - travel_matrix once for [BASE + ordered]
    - returns consecutive RouteLeg chain for that order
  This is SEPARATE from OptimizeResult.legs. Do NOT wire it as a drop-in replacement
  for optimize_route's legs field.

─── RULES ───

  - No permutation search inside polyline helper
  - travel_engine purity unchanged
  - Do not duplicate the polyline for-loop elsewhere

─── FAILURE BOUNDARY ───

  route_polyline failures stay soft (None) — no new failure modes.

─── DO NOT ───

  - Replace OptimizeResult.legs with consecutive-only legs
  - Add DayPlan / ScheduledStop polyline fields
  - Change drop-retry / permutation scoring

✅ Validation:
  - Existing P4/P6 route_optimizer polyline tests still green
  - Fake three-stop optimize: len(legs) == full pairwise size (12), len(leg_polylines) == 3
  - python -m pytest tests/travel_engine/ -v  (route optimizer subset) green

✅ Failure path: all-None polylines still return ordered OptimizeResult without raise
```

---

## Step 7.2 — TripService edit operations + preserve-order schedule

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement day-surgery service methods + schemas + exceptions, using shared polyline
helper from 7.1, preserve-order schedule for reorder, and v2.1 drop/audit locks.
This is step 7.2. No FastAPI routes yet (7.3). Wire RoutingProvider via constructor default
OsrmRoutingProvider() or optional routing= for tests. No new packages. No PlannerService /
execute_tool / LLM.

─── EXTEND src/travel_engine/schedule_builder.py ───

  Add preserve-order entry — either:
    build_day_schedule_preserve_order(ordered_stops, route_legs)
  or:
    build_day_schedule(..., *, preserve_order: bool = False)

  When preserve_order=True: SKIP _extract_morning_first; time stops in the given order.
  Default False: existing morning-extract behavior unchanged (generation + non-reorder edits).

  Optionally prefix check_morning_slots error strings with "morning_slot_violation: "
  in trip_validator.py (string-only, backward compatible) so TripService can filter.

─── EXTEND src/trips/exceptions.py ───

  class TripEditValidationError(WandrError):
      """422 — validation or business rule failed; trip unchanged."""
      def __init__(self, message: str, *, code: str = "trip_edit_validation_failed",
                   details: dict | None = None):
          super().__init__(message, code=code, status_code=422, details=details or {})

  class TripStopConflictError(WandrError):
      """409 — place already on trip."""
      def __init__(self, message: str = "stop already on trip"):
          super().__init__(message, code="stop_already_on_trip", status_code=409)

  class TripStopNotFoundError(WandrError):
      """404 — place_id not on that day."""
      def __init__(self, message: str = "stop not found on this day"):
          super().__init__(message, code="stop_not_found_on_day", status_code=404)

─── EXTEND src/trips/schemas.py ───

  class ReorderStopsIn(BaseModel):
      place_ids: list[uuid.UUID]

  class AddStopIn(BaseModel):
      place_id: uuid.UUID

─── EXTEND src/trips/repository.py (as needed) ───

  Flush-only helpers if missing:
  - delete TripPlace by (trip_id, place_id, day)
  - update order/times/polyline fields
  - insert TripEditEvent   # TripRepository SOLE writer of this row
  TripPlace is hard-deleted (no SoftDeleteMixin).

─── EXTEND src/trips/service.py — private helpers ───

  _hydrate_scored(trip_place) -> ScoredPlace
    PlaceCandidate from joined Place (to_shape → lat/lng; category; name;
    enriched_tags). score=1.0, score_breakdown={}.

  _snapshot_day(places_for_day) -> list[dict]
    {place_id, order_in_day, travel_time_min, visit_duration_min,
     suggested_start_time, polyline} — call BEFORE mutation for "before".

  async def _fixed_order_day(scored_in_order, base_lat, base_lng, routing):
      # travel_matrix once; consecutive legs for that order;
      # leg_polylines, day_polyline = await populate_leg_polylines(...)
      # return ordered, consecutive_legs, leg_polylines
      # MUST NOT call optimize_route / MUST NOT permute

  async def _optimize_day(...) -> OptimizeResult:
      return await optimize_route(...)

  def _schedule_mutated_day(ordered, legs, *, preserve_order: bool) -> list[ScheduledStop]:
      if preserve_order:
          return build_day_schedule_preserve_order(ordered, legs)  # or flag
      return build_day_schedule(ordered, legs)

  # Persist path: keep leg_polylines PARALLEL to ScheduledStop list.
  # Zip onto TripPlace.polyline at write time.
  # DO NOT assign stop.leg_polyline or DayPlan.day_polyline — those fields do not exist.

  async def _validate_full_trip(trip, mutated_day_number, new_day_plan, *, edit_type) -> None:
      # Mutated day = new_day_plan
      # OTHER days: reconstruct ENTIRELY from stored TripPlace fields
      #   total_travel_min = sum(stop.travel_time_min for stop in day_stops)
      #   ZERO RoutingProvider calls for unchanged days
      # validate_trip(itinerary)
      # If edit_type == REORDER: move errors matching morning_slot_violation* into warnings
      # Any remaining errors → TripEditValidationError(details={errors, warnings})

  async def _persist_day_and_audit(...) -> Trip:
      # UoW single commit:
      # 1. Apply TripPlace mutations for the day (incl. polyline from leg_polylines zip)
      # 2. TripRepository.insert_edit_event(... payload before/after ...)
      # 3. await EvaluationService(session).mark_trip_edited(trip.id)  # flag only
      #    (7.5 may land stub no-op first; preferred: call final name even if thin)
      # 4. commit; return get_with_places

─── PUBLIC METHODS ───

  async def reorder_stops(self, trip_id, day, place_ids, user_id, *, routing=None) -> Trip
  async def remove_stop(self, trip_id, day, place_id, user_id, *, routing=None) -> Trip
  async def add_stop(self, trip_id, day, place_id, user_id, *, routing=None) -> Trip
  async def reoptimize_day(self, trip_id, day, user_id, *, routing=None) -> Trip

  Common preamble:
    - load trip with places (404 if missing)
    - if trip.user_id != user_id: raise TripForbiddenError
    - resolve destination; base = _resolve_base(...)
    - before = _snapshot_day(current day)  # BEFORE mutation
    - filter places for day_number == day
    - add onto empty day is allowed; remove that would empty is not

  reorder_stops:
    - require len(place_ids)==len(current) and set(place_ids)==set(current); else 422
    - order scored by place_ids
    - _fixed_order_day → schedule preserve_order=True → validate (REORDER downgrade) → persist
    - EditType.REORDER

  remove_stop:
    - not on day → TripStopNotFoundError 404
    - len(day_stops)==1 → TripEditValidationError code day_would_be_empty
    - remaining → optimize_route; if dropped_stops: 422 edit_would_drop_other_stops
    - schedule default → validate → persist
    - EditType.REMOVE_STOP

  add_stop:
    - Place missing → 404; wrong destination → 422; already on trip → 409
    - append → optimize_route; if dropped_stops → 422 edit_would_drop_other_stops (details)
    - schedule default → validate → persist
    - EditType.ADD_STOP

  reoptimize_day:
    - optimize_route; same dropped_stops → 422 rule
    - schedule default → validate → persist
    - EditType.REOPTIMIZE_DAY

  Note: still_over_budget with empty dropped_stops (single over-budget stop) normally fails
  travel-cap validate → 422. Do not treat dropped_stops as the only overload signal.

─── RULES ───

  - Concurrency: last-write-wins; comment on TripService; no row locking in P7
  - Never leave half-updated day committed
  - Never call LLM / PlannerService / execute_tool

─── DO NOT ───

  - Register routes (7.3)
  - Cross-day move / chat replan / new tables
  - Reimplement polyline loop outside populate_leg_polylines
  - Invent ScheduledStop.leg_polyline / DayPlan.day_polyline

✅ Validation:
  - TripService has reorder_stops, remove_stop, add_stop, reoptimize_day
  - Unit/Fake: reorder preserves order + polylines on TripPlace; remove last → error;
    add duplicate → 409; add that would drop → 422, no mutation

✅ Failure path: validation failure → rollback; no TripEditEvent row
✅ Failure path: add forcing drop → TripEditValidationError; zero TripPlace changes
```

---

## Step 7.3 — trips/router.py edit endpoints + rate limit

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Expose the four blueprint edit endpoints with user-keyed rate limit. This is step 7.3.
Reuse TripService from 7.2. Return ApiResponse[TripOut]. No new packages.

─── UPDATE src/config.py ───

  RATE_LIMIT_TRIP_EDIT_REQUESTS: int = 20
  RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS: int = 60

─── ADD 429 exception if missing ───

  RateLimitedError does not exist today — middleware returns ErrorResponse inline.
  Add a small WandrError subclass (status_code=429, code="rate_limit_exceeded") OR raise
  WandrError with those fields from the dependency. Reuse existing handler mapping.

─── IMPLEMENT rate_limit_trip_edit dependency ───

  async def rate_limit_trip_edit(payload: TokenPayload = Depends(require_auth)) -> TokenPayload:
      settings = get_settings()
      limiter = get_rate_limiter()
      key = f"{payload.user_id}:trip_edit"
      try:
          allowed, _ = await limiter.is_allowed(
              key,
              settings.RATE_LIMIT_TRIP_EDIT_REQUESTS,
              settings.RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS,
          )
      except Exception:
          return payload  # fail open
      if not allowed:
          raise RateLimitedError(...)  # or WandrError 429
      return payload

  Do NOT add UUID edit paths to _route_limit_table.
  Document: middleware IP default may still apply (dual limit OK).

─── EXTEND src/trips/router.py ───

  PATCH /{trip_id}/days/{day}/stops/reorder  body ReorderStopsIn  Depends(rate_limit_trip_edit)
  DELETE /{trip_id}/days/{day}/stops/{place_id}  Depends(rate_limit_trip_edit)
  POST /{trip_id}/days/{day}/stops  body AddStopIn  Depends(rate_limit_trip_edit)
  POST /{trip_id}/days/{day}/reoptimize  Depends(rate_limit_trip_edit)

  day: int path (1-based day_number). Pass payload.user_id into service.
  Map domain errors via existing exception handlers.

─── FAILURE BOUNDARY ───

  - Unauthenticated → 401
  - Non-owner → 403
  - Rate limited → 429
  - Service validation → 422
  - Conflict → 409
  - Stop not found → 404
  - Router: no DB / no travel_engine imports

─── DO NOT ───

  - optional_auth on edits
  - Return raw dict
  - Import redis / litellm

✅ Validation:
  - OpenAPI lists four new routes
  - Owner reorder → 200 TripOut; GeoJSON reflects polylines when present
  - Guest → 401; other user → 403
  - 21st rapid edit same user within window → 429 (mock limiter in unit test)

✅ Failure path: add overload / would-drop → 422; re-GET matches pre-edit
```

---

## Step 7.4 — tests/trips/test_edit_replan.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Pytest coverage for P7 edit/replan including v2.1 regressions. This is step 7.4.
Use FakeRoutingProvider. Prefer service-level tests + thin HTTP for auth + rate limit.

─── CREATE tests/trips/test_edit_replan.py ───

  Required scenarios:
  1. reorder — order_in_day matches client; times + TripPlace.polyline updated
  2. reorder preserves order even with morning-only category mid-list (preserve-order)
  3. remove_stop — stop gone; remaining re-routed
  4. remove last stop — 422 day_would_be_empty; unchanged
  5. remove place not on day — 404 stop_not_found_on_day
  6. add_stop — new TripPlace; polyline populated
  7. add duplicate — 409
  8. add wrong destination — 422
  9. add that forces dropped_stops — 422 edit_would_drop_other_stops; zero place changes
 10. reoptimize_day — success with Fake
 11. reoptimize that forces drop — same 422 as add
 12. ownership — wrong user → 403
 13. OSRM fallback — None polyline → success (no 500)
 14. reorder morning-slot-only validate → 200 + warnings + commit
 15. remove/add/reoptimize morning-slot errors → still 422 (no downgrade)
 16. reorder duplicate ids → 422
 17. successful edit → exactly one TripEditEvent (not 0 or 2)
 18. validation failure → rollback; TripEditEvent count unchanged
 19. spy: RoutingProvider calls only for mutated day on multi-day trip
 20. rate limit — mock limiter → 429 on over-quota

─── FAILURE BOUNDARY ───

  Tests must not require live OSRM or LLM.
  DB: wandr_test / existing fixtures from tests/trips/.

─── DO NOT ───

  - Hit real OSRM in CI unit tests
  - Skip ownership, rollback, or v2.1 regression cases

✅ Validation:
  python -m pytest tests/trips/test_edit_replan.py -v  → green
  python -m pytest tests/ -v  → green

✅ Failure path: test asserts rollback — TripEditEvent count unchanged on failed add
```

---

## Step 7.5 — EvaluationService.mark_trip_edited (flag only)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Honor AGENT.md — evaluation reflects every edit. This is step 7.5.
LOCKED: this step does NOT create TripEditEvent — TripService already owns that write.

─── EXTEND src/evaluation/repository.py ───

  async def get_latest_for_trip(self, trip_id: UUID) -> TripEvaluation | None
  async def mark_user_edited(self, evaluation: TripEvaluation) -> TripEvaluation
    # set user_edited=True; flush only

─── EXTEND src/evaluation/service.py ───

  async def mark_trip_edited(self, trip_id: UUID) -> None:
      """
      Flag only. Does NOT create TripEditEvent.
      No evaluation row → no-op. No LLM. No planner.
      """
      evaluation = await self.repo.get_latest_for_trip(trip_id)
      if evaluation is not None and not evaluation.user_edited:
          await self.repo.mark_user_edited(evaluation)

─── WIRE TripService ───

  After TripEditEvent insert, call mark_trip_edited in same session before commit.

─── FAILURE BOUNDARY ───

  - No evaluation → no-op; edit succeeds
  - Keep flag update in-UoW (same transaction)

─── DO NOT ───

  - Create TripEditEvent here
  - New TripEvaluation columns / migrations
  - Evaluation HTTP routes

✅ Validation:
  - Edit with evaluation → user_edited True
  - Edit without evaluation → TripEditEvent exists; 200
  - Spy: mark_trip_edited inserts zero trip_edit_events rows

✅ Failure path: missing evaluation does not block edit
```

---

## Step 7.6 — Smoke + context.md ship

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Close P7 documentation checkpoint. Optional live smoke. This is step 7.6.
Only mark context.md after pytest (and smoke if present) are green.

─── OPTIONAL scripts/test_p7_smoke.py ───

  If written: owned trip; reorder day 1; assert exactly one TripEditEvent;
  assert GeoJSON shows polyline when present. Offline Fake preferred;
  live OSRM optional behind env flag.

─── UPDATE docs/context.md ───

  - Last updated = today; Next step = post-P7 / production readiness
  - Progress: 7.0–7.6 ✅
  - Current state: P7 done — day edit/replan HTTP + TripEditEvent; shared polyline helper;
    preserve-order reorder
  - Implemented modules: edit methods, routes, rate_limit_trip_edit, mark_trip_edited,
    populate_leg_polylines, preserve-order schedule
  - Live endpoints: four edit rows
  - Known MVP limitation: concurrent edits last-write-wins
  - Stubs only: remove “P7 trip edit/replan HTTP still stubs”
  - Do NOT claim evaluation HTTP done

─── IMPORT GUARDS ───

  Spot-check: trips edit modules do not import litellm, langgraph, PlannerService,
  execute_tool, redis.

─── FAILURE BOUNDARY ───

  - Do not update context.md if tests fail

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

## P7 ship criteria (v2.1)

| Check | Expected |
|-------|----------|
| Base prefs | `save_from_state` stores `base_lat`/`base_lng` when present |
| Resolve base | prefs win; else Destination |
| Shared polyline helper | used by optimize_route **and** reorder; OptimizeResult.legs stays full pairwise |
| Reorder | User order preserved (no TSP, no morning extract); times + TripPlace.polyline refreshed |
| Remove / add / reoptimize | `optimize_route` path; polylines zipped at persist |
| Dropped-stops on add/reoptimize | 422, not silent mutation |
| Empty day | 422; unchanged |
| Bad / duplicate reorder list | 422 via `len`+`set` |
| Stop not on day | 404 |
| Validation | 422 + rollback — except reorder morning-slot-only → 200 + warnings |
| Unchanged days | Zero extra routing calls |
| OSRM fallback | 200 not 500 |
| Auth + rate limit | require_auth; non-owner 403; user-keyed 429 |
| Audit | Exactly one TripEditEvent by TripService; `mark_trip_edited` flag-only |
| Layering | No PlannerService / execute_tool / LLM / litellm / langgraph on edit path |
| Envelope | `ApiResponse[TripOut]` |
| GeoJSON | Reflects post-edit polylines without new endpoint |
| Concurrency | Documented MVP last-write-wins |
| pytest | `test_edit_replan` + full suite green |
| context.md | Updated only on 7.6 after green |

---

## Recommended OpenSpec implementation batches

This planning change (`harden-p7-step7-prompt`) authors **this file** + specs only.

After P6.5 is green **and** this `docs/steps/step7.md` is the SoT, apply code as **separate**
OpenSpec implementation changes (or batched `/opsx:apply` sessions), in order:

1. `7.0` — base coords on preferences + `_resolve_base`
2. `7.1` — `populate_leg_polylines` (keep full pairwise legs)
3. `7.2` — preserve-order schedule + TripService edit ops (TripService owns TripEditEvent)
4. `7.3` — four router endpoints + `rate_limit_trip_edit`
5. `7.4` — `tests/trips/test_edit_replan.py`
6. `7.5` — `EvaluationService.mark_trip_edited`
7. `7.6` — smoke (optional) + `docs/context.md`

Do **not** open a full propose→archive cycle for each micro-detail unless a design conflict
appears. If implementation reality conflicts with a lock: **amend this file first**, then code
(minimal replan). Sync/archive OpenSpec deltas when appropriate — do not hand-edit
`openspec/specs/` outside that workflow.
