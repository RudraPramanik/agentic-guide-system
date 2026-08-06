Verdict on the P7 draft

This is a genuinely careful draft — the "naming trap" callout (P5's AgentPhase.REPLAN vs P7's HTTP edit/replan) is exactly the kind of thing that prevents a real implementation mistake, the base-coordinates gap (Trip never persisted base_lat/base_lng, so edits would have invented an origin) was caught and fixed proactively, and the ownership/failure-mode tables are thorough. But tracing this against what P4's route-geometry patch actually produces, and reading the document's own two edit-audit steps against each other, surfaced one outright internal self-contradiction and three other issues substantial enough that I rebuilt the file rather than patch it in place.

🔴 Critical

1. The document contradicts itself on who creates TripEditEvent. Step 7.1's own pseudocode says "Preferred: 7.1 inserts TripEditEvent in UoW; calls record_edit if available." Step 7.4 says "Option A (LOCKED): EvaluationService.record_edit creates the TripEditEvent; TripService... does not insert the event itself." These are opposite answers to the same question, both presented with directive language, in the same document. Left as-is, this is a coin-flip for whoever implements it — either a double-inserted audit row or a missing one. I resolved it in favor of domain ownership: TripEditEvent lives in trips/models.py, so TripService creates it, in the same transaction as the place mutations, from step 7.2 onward. EvaluationService is narrowed to a single, purely additive method — mark_trip_edited(trip_id) — that only flips the user_edited flag on the linked evaluation, called after the event already exists.

2. Nothing shares the route-geometry logic between generation and edits, so they will drift. My P6 rebuild added route_optimizer.optimize_route()'s polyline computation (matrix once + N+1 route_polyline calls) inline, for the winning permutation. This P7 draft's reorder path (_fixed_order_day) needs the exact same "given a fixed order, compute legs + polylines" capability — but since that logic isn't factored out anywhere, P7 would have to reimplement it from scratch, duplicated, with a real risk of the two copies silently diverging over time. I extracted a shared compute_legs_and_polylines() function in travel_engine/route_optimizer.py that both optimize_route() (for the winning permutation) and P7's reorder path (for the user's explicit order, no permutation search) call — single source of truth.

3. The draft's edit-time DayPlan construction never mentions carrying polylines through. _day_plan_from_result's pseudocode builds DayPlan(stops=..., total_travel_min=..., dropped_stops=...) with no polyline field at all — meaning every edit operation would silently regress TripPlace.polyline back to None, even though the data is sitting right there in optimize_route's result. A user reorders their trip, and the map quietly loses its route line. Fixed explicitly in the rebuild.

4. add_stop/reoptimize_day can silently remove a different stop than the one the user asked to change. If adding a place pushes the day over MAX_DAILY_TRAVEL_MIN, optimize_route's own internal drop-retry (from P4) will drop the lowest-scored stop to compensate — which could easily be a stop the user was happy with and never asked to touch. As drafted, this would just... happen, silently, on commit. That's an unrequested side-effect on someone's saved trip. I locked this as a validation failure instead: if the result comes back with any dropped_stops, roll back and return 422 naming what would have been dropped, so the user can decide (remove something else first, or pick a different day) rather than have it decided for them.

🟠 Moderate
_validate_full_trip's "recompute lightly" for unchanged days is exactly ambiguous enough to violate the document's own stated efficiency principle ("touch one day for matrix/polyline"). If read as "re-run travel_matrix for every day to be safe," a single-day edit turns into a multi-day OSRM bill. Locked: unchanged days are reconstructed entirely from already-persisted TripPlace fields (total_travel_min = sum(stop.travel_time_min for stop in day_stops)) — zero new network calls for anything the user didn't touch.
The reorder permutation check's phrasing ("sorted as sets and same length") is genuinely ambiguous and could be implemented as a bare set-equality check that misses duplicate-ID submissions. Locked to the precise, unambiguous check: len(place_ids) == len(current_ids) and set(place_ids) == set(current_ids).
remove_stop on a place not on that day is left as "404 or 422 (prefer 404)" — another unresolved either/or. Locked to 404 with a distinct code (stop_not_found_on_day), consistent with how every other "resource not found" case in this codebase behaves.
Rejecting a user's own explicit reorder because it puts a viewpoint outside "morning slots" is poor UX for a feature whose entire point is letting the user control the order. check_morning_slots is a scheduling preference the algorithm applies during generation, not a physical constraint like a travel-time cap. I locked a reorder-specific rule: morning-slot violations are downgraded to warnings (commit proceeds) only for the reorder endpoint; every other validation rule, and every other edit type, stays a hard error.
No concurrency protection on simultaneous edits to the same trip. Two tabs editing the same day is a real last-write-wins race as drafted. Documented explicitly as an accepted MVP limitation rather than left silently unaddressed — worth revisiting with row-level locking once multi-device editing is a real usage pattern.
Edit routes inherit the global default rate limit, but each edit call can trigger up to ~7 OSRM requests — the same class of "hammer a rate-limited external service" risk I flagged for Nominatim back in P2. Since these routes already require full auth, I added a route-level, user-keyed limiter (not a path-string middleware match, which can't handle UUID segments cleanly) — arguably better than IP-based limiting here anyway, since it can't be evaded by switching networks

---


# Wandr — P7 Cursor Prompts: Edit & Replan API (v2 — hardened)
> Blueprint SoT: [`docs/blueprint_final.md`](../blueprint_final.md) **v6.1** — Phase P7 (2 days · 4 blueprint steps, expanded here to **7.0–7.6**)
> Built-so-far context: [`docs/context.md`](../context.md) · Guardrails: [`AGENT.md`](../../AGENT.md)
> **Supersedes** the prior P7 draft. **v2 changelog:** resolves a direct internal contradiction
> over who creates `TripEditEvent` (the prior draft's step 7.1 and step 7.4 gave opposite,
> both-"locked"/"preferred" answers), extracts a shared route-geometry helper so reorder and
> generation-time optimization can never drift apart, fixes a silent polyline-loss-on-edit gap,
> stops `add_stop`/`reoptimize_day` from silently dropping a stop the user never asked to touch,
> locks the "recompute lightly" ambiguity to a true zero-extra-network-call guarantee for
> unchanged days, and adds a user-keyed rate limit on the edit routes.
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
> **Gate:** do not implement P7 code batches until P6.5 is green in `docs/context.md`,
> `RoutingProvider.route_polyline()` (P6's step 6.0 patch) is real, and `TripService.save_from_state`
> persists `base_lat`/`base_lng`-carrying schedules with polylines end to end.

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
call `execute_tool`, and does **not** use `PlannerService`. Blueprint wording "travel_engine +
tools" means **the same algorithms tools use**, not `TOOL_REGISTRY`.

---

## Decision / Fix Log (read before implementing)

| # | Risk if unlocked | Lock in this prompt |
|---|---|---|
| 1 | Agent confuses P5 REPLAN with P7 HTTP | Callout above; never import planner tools / graph on edit path |
| 2 | `TripService` calls `execute_tool` / `PlannerService` | Edit ops → `travel_engine` + injected `RoutingProvider` only |
| 3 | `Trip` has no base coords → optimize invents origin | **7.0:** persist `base_lat`/`base_lng` on `Trip.preferences`; edits use `_resolve_base` (prefs → else Destination) |
| 4 | Reorder silently TSP-permutes user's order | Reorder = fixed-order geometry via the **shared** `compute_legs_and_polylines` helper — **no** permutation search |
| 5 | Remove/add/reoptimize skip re-route | Those three **do** call `optimize_route` (which internally uses the same shared helper for the winning order) |
| 6 | Hydration invents scores / skips Place fields | `ScoredPlace(score=1.0)`; lat/lng via `to_shape`; category/name/`enriched_tags` from Place |
| 7 | Empty day after remove | **422** `day_would_be_empty` — day must keep ≥1 stop |
| 8 | Validation fail still commits | `validate_trip` errors → rollback → **422**; warnings alone OK |
| 9 | OSRM timeout → 500 | Fail-soft haversine / null polyline → **200** (existing provider behavior) |
| 10 | Guest edits via `wandr_session` | All four routes `require_auth` + `trip.user_id == caller`; claim first (P6's `POST /trips/{id}/claim`) |
| 11 | Duplicate place / wrong destination on add | Duplicate → **409** `stop_already_on_trip`; wrong dest → **422** |
| 12 | Bad reorder list | Not an exact permutation (right members, right count, no dupes) of that day's place_ids → **422** |
| 13 | Edit skips audit / evaluation | Same UoW: TripPlaces + `TripEditEvent` + `user_edited` flag, one commit |
| 14 | Edit routes unrate-limited against OSRM cost | User-keyed route-level limiter (not global default), since each edit can cost ~7 OSRM calls |
| 15 | LLM / narrative on edit | Forbidden — times/order/geometry from travel_engine + RoutingProvider only |
| 16 ★ | **v1 self-contradiction:** step 7.1 said "TripService inserts TripEditEvent," step 7.4 said "LOCKED: EvaluationService creates it" — opposite answers in the same doc | **Resolved:** `TripService` creates `TripEditEvent` (it's a trips-domain model, same UoW as the mutation). `EvaluationService` gets a narrow, additive `mark_trip_edited(trip_id)` that only sets the `user_edited` flag — it never creates the event |
| 17 ★ | Reorder and generation each compute route geometry independently → drift risk | Shared `compute_legs_and_polylines()` in `travel_engine/route_optimizer.py`, called by **both** `optimize_route()` (winning permutation) and P7's reorder (user's fixed order) |
| 18 ★ | Edit-time `DayPlan` construction drops `leg_polylines`/`day_polyline` → GeoJSON silently regresses on every edit | `_day_plan_from_result` explicitly carries both through to persisted `TripPlace.polyline` |
| 19 ★ | `add_stop`/`reoptimize_day` can silently drop a stop the user never asked to touch, to make room for the requested change | Non-empty `dropped_stops` from `optimize_route` → treated as a validation failure (422, rollback), never a silent side-effect |
| 20 ★ | "Other days recompute lightly" ambiguous enough to blow the stated "touch one day" efficiency principle | Locked: unchanged days reconstructed **entirely** from stored `TripPlace` fields — zero new network calls |
| 21 ★ | Rejecting a user's own explicit reorder over morning-slot placement undermines the feature's purpose | Reorder-only: morning-slot violations downgrade to warnings (commit proceeds); every other rule, and every other edit type, stays a hard error |
| 22 ★ | No documented stance on concurrent edits to the same trip | Explicit MVP limitation: last-write-wins, no row locking — stated, not silently absent |

★ = new in v2, found by tracing the draft against P6's route-geometry patch and against itself.

---

## Prerequisites (P6 must be complete)

Before step 7.0, confirm from `docs/context.md`:

- All P6 steps ✅ — trips HTTP CRUD + GeoJSON + claim; planner SSE; **`RoutingProvider.route_polyline()` real** (P6 step 6.0); `TripPlace.polyline` populated on generation; cache backends
- `python -m pytest tests/ -v` green
- `python scripts/test_p6_smoke.py` green (or documented equivalent)
- **Already real (do NOT reinvent):**
  - `src/trips/models.py` — `Trip`, `TripPlace`, `TripEditEvent`, `EditType`
  - `src/trips/service.py` — `save_from_state`, ownership, `claim_for_user`, `build_geojson`
  - `src/trips/router.py` — list/get/delete/geojson/claim
  - `src/trips/schemas.py` — `TripOut`, `TripPlaceOut`
  - `src/planner/routing_provider.py` — `OsrmRoutingProvider` (`travel_matrix` + `route_polyline`)
  - `src/travel_engine/*` — `optimize_route` (now returning `leg_polylines`/`day_polyline`), `build_day_schedule`, `validate_trip`, protocols, rules
  - `src/evaluation/service.py` — `record_generation` only
  - Destination model with `lat`/`lng`
- **Still stub / missing for P7:**
  - `compute_legs_and_polylines` shared helper (this document adds it — step 7.1)
  - Edit ops on `TripService`
  - Four edit HTTP routes + their rate limiter
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
  7.1 travel_engine/route_optimizer.py — extract compute_legs_and_polylines
        │     (shared by optimize_route AND P7's fixed-order reorder path)
        │
  7.2 TripService day surgery (reorder / remove / add / reoptimize_day)
        │     hydrate → travel_engine + RoutingProvider → validate → UoW
        │     TripService creates TripEditEvent directly (resolves v1's contradiction)
        │
  7.3 trips/router.py — four endpoints (require_auth + ownership + user-keyed rate limit)
        │
  7.4 tests/trips/test_edit_replan.py
        │
  7.5 EvaluationService.mark_trip_edited (narrow — flag only, does not create the event)
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
       ├─► reorder: compute_legs_and_polylines(user's fixed order, ...)   ── SHARED helper
       │   remove/add/reoptimize: optimize_route(...) which internally calls the
       │       SAME shared helper for whichever order it picks
       ├─► if optimize_route returned dropped_stops → 422, rollback (v2 new rule)
       ├─► rebuild TripItinerary: mutated day = new DayPlan (with polylines);
       │         OTHER days reconstructed ENTIRELY from stored TripPlace fields,
       │         zero new network calls (v2 locked)
       ├─► validate_trip; for REORDER only, downgrade morning_slot_violation
       │         errors to warnings (v2 new rule); all else stays a hard error
       │         errors remaining? → rollback → TripEditValidationError 422
       ├─► mutate TripPlaces (incl. polyline column) + insert TripEditEvent (TripService owns this)
       ├─► EvaluationService.mark_trip_edited(trip_id)  (flag only, same UoW)
       └─► commit → reload → TripOut
```

---

## Shared locks (apply to all P7 steps)

### Auth matrix — LOCKED

| Method | Path | Auth |
|--------|------|------|
| PATCH | `/api/v1/trips/{id}/days/{day}/stops/reorder` | `require_auth` + owner + rate_limit_trip_edit |
| DELETE | `/api/v1/trips/{id}/days/{day}/stops/{place_id}` | `require_auth` + owner + rate_limit_trip_edit |
| POST | `/api/v1/trips/{id}/days/{day}/stops` | `require_auth` + owner + rate_limit_trip_edit |
| POST | `/api/v1/trips/{id}/days/{day}/reoptimize` | `require_auth` + owner + rate_limit_trip_edit |

Owner = `trip.user_id == payload.user_id`. Unclaimed / guest session alone → **403** (claim via P6's `POST /trips/{id}/claim` first). Soft-deleted / missing → **404**. Wrong owner → **403** (not 404).

Existing P6 routes unchanged.

### Failure-mode table — LOCKED (v2)

| Failure | Behavior |
|---------|----------|
| Not authenticated | 401 |
| Not owner / unclaimed | 403 |
| Trip missing / soft-deleted | 404 |
| Reorder not an exact permutation (`len` equal AND `set` equal — catches missing/extra/duplicate IDs) | 422 |
| Stop referenced in `remove_stop` not on that day | **404** `stop_not_found_on_day` (v2 locked — was "404 or 422" in v1) |
| Remove last stop on day | 422 `day_would_be_empty` |
| Add place already on trip | 409 `stop_already_on_trip` |
| Add place wrong destination | 422 |
| `optimize_route` returns non-empty `dropped_stops` for add/reoptimize | **422** `edit_would_drop_other_stops` (v2 new — was a silent side-effect in v1), details list what would have been dropped |
| `validate_trip` errors (non-reorder, or reorder with non-morning-slot errors) | 422 + rollback; `details` include errors (+ warnings) |
| `validate_trip` morning-slot errors on **reorder specifically** | Downgraded to warnings; 200 OK, commit proceeds (v2 new) |
| `validate_trip` warnings only | 200 OK (commit) |
| OSRM timeout / fallback | 200; times from haversine; polylines may be `None` |
| Partial DB write | Full transaction rollback |
| Concurrent edits to same trip/day | **Documented MVP limitation** — last-write-wins, no row locking (v2 — stated explicitly, not silently absent) |

### Abstraction & provider swap — LOCKED

| Concern | Protocol / gateway | Dev | Prod | Swap |
|---------|-------------------|-----|------|------|
| Routing (matrix + polyline) | `RoutingProvider` | Fake in tests | `OsrmRoutingProvider` | ctor / param DI into TripService edit helpers |
| Route geometry computation | `compute_legs_and_polylines` (shared) | same fn, Fake provider | same fn, Osrm provider | no duplication between generate/edit |
| Travel algorithms | pure `travel_engine` | same | same | no I/O |
| Auth | `require_auth` | JWT | JWT | existing |
| Edit rate limit | `RateLimiterBackend` (existing Protocol) | in-memory | Redis (if configured) | `get_rate_limiter()`, keyed by user_id not path |
| Cache / Redis | unchanged | — | — | **not used by P7 edits** |

Trips router MUST NOT `import redis`, `litellm`, or `langgraph`.

### Design patterns — LOCKED

| Module | Pattern | Meaning |
|--------|---------|---------|
| Edit UoW | Unit of Work | TripPlaces + TripEditEvent + eval flag, one commit |
| `RoutingProvider` | Protocol / DI | Same as planner tools; Fake in tests |
| `compute_legs_and_polylines` | Extract Method | Single source of truth for "order → geometry," shared by generation and edit |
| Ownership | Policy / Guard | Auth + `user_id` match (stricter than guest GET) |
| `validate_trip` | Chain of Responsibility | Existing P4 rules — do not fork; reorder-specific downgrade happens in TripService, not in the validator itself |
| Router → Service | Service Layer | No DB in router |

### Code quality & system design principles — LOCKED

1. **Single responsibility:** HTTP parsing in router; mutation + routing orchestration in service; flush-only writes in repository.
2. **Determinism:** same inputs + FakeRoutingProvider → same order/times/polylines in tests.
3. **Fail closed on business rules** (validation, empty day, ownership, unrequested side-effects); **fail soft on external routing**.
4. **Efficiency:** touch **one day** for matrix/polyline; unchanged days cost **zero** additional network calls; do not re-run the full multi-day agent loop; reorder skips permutations entirely.
5. **Auditability:** every successful edit → `TripEditEvent` with before/after payload, created by the same domain (`trips`) that owns the mutation.
6. **No silent side-effects:** an edit never mutates something the caller didn't ask to change (see rule #19 — dropped-stops-on-add is a rejection, not a silent extra mutation).
7. **No speculative abstraction beyond what's proven necessary:** `compute_legs_and_polylines` is extracted because two real callers need it identically — do not extract further shared "day surgery" machinery unless a third caller appears (forward lock F5).

### Forward locks (design-only — do not implement in P7)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | Chat / LLM "replan my whole trip" | post-P7 product |
| F2 | Evaluation HTTP API | later |
| F3 | Row-level locking for concurrent edits to the same trip | if multi-device concurrent editing becomes a real usage pattern |
| F4 | Dedicated `Trip.base_lat` columns (vs preferences JSON) | only if prefs prove awkward |
| F5 | Shared day-surgery helper beyond `compute_legs_and_polylines` | if duplication hurts further |

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

## Step 7.1 — Extract shared route-geometry helper ★ NEW (v2)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Extract compute_legs_and_polylines from route_optimizer.optimize_route() so BOTH
generation-time optimization AND P7's fixed-order reorder can call the exact same "given an
order, compute geometry" logic — closing the duplication/drift risk flagged in the v2 review.
This is step 7.1. No new packages. Touches src/travel_engine/route_optimizer.py (P4/P6 file).

─── EXTEND src/travel_engine/route_optimizer.py ───

  async def compute_legs_and_polylines(
      ordered: list[ScoredPlace],
      base_lat: float,
      base_lng: float,
      routing: RoutingProvider,
  ) -> tuple[list[RouteLeg], list[str | None], str | None]:
      """
      Given an ALREADY-DECIDED order (no permutation search performed here), compute:
        - legs: consecutive RouteLeg objects (base->first, first->second, ...)
        - leg_polylines: aligned to `ordered`, index i = polyline INTO ordered[i]
        - day_polyline: aggregate polyline for the whole day (all waypoints in order)

      SINGLE SOURCE OF TRUTH for "given an order, compute geometry" — called by:
        1. optimize_route() below, for the winning permutation after search
        2. TripService's reorder path (P7, step 7.2), for the user's explicit fixed order
      These two callers must never independently reimplement this logic — that's the
      duplication/drift risk this extraction exists to close.
      """
      waypoints = [(BASE_SENTINEL_ID, base_lat, base_lng)] + [
          (sp.place.id, sp.place.lat, sp.place.lng) for sp in ordered
      ]
      matrix = await routing.travel_matrix(waypoints)
      lookup = legs_to_lookup(matrix)
      legs = [
          lookup.get((waypoints[i][0], waypoints[i + 1][0]))
          for i in range(len(waypoints) - 1)
      ]
      coords = [(w[1], w[2]) for w in waypoints]
      leg_polylines = [
          await routing.route_polyline(coords[i : i + 2]) for i in range(len(ordered))
      ]
      day_polyline = await routing.route_polyline(coords) if len(coords) >= 2 else None
      return legs, leg_polylines, day_polyline

─── REFACTOR optimize_route() to USE this helper ───

  After the winning permutation is selected (existing brute-force search logic unchanged),
  REPLACE the inline leg/polyline computation added in P6's step 6.0 with a call to:

      legs, leg_polylines, day_polyline = await compute_legs_and_polylines(
          ordered, base_lat, base_lng, routing,
      )

  OptimizeResult's shape is unchanged (still has legs, leg_polylines, day_polyline) — this
  is a pure refactor, not a behavior change. Existing P4/P6 tests for optimize_route must
  still pass unmodified after this refactor.

─── RULES ───
- compute_legs_and_polylines performs NO permutation search — it trusts the order it's given.
- travel_engine purity unchanged — this still only calls the injected RoutingProvider, no
  direct geo/httpx/DB imports.
- Do not duplicate this logic anywhere else. If a third caller needs it later, import from
  here — do not copy-paste.

─── FAILURE BOUNDARY ───
routing.travel_matrix / route_polyline failures propagate their existing fallback behavior
(None polylines, degraded legs) — this function adds no new failure modes, it only
consolidates existing ones into one place.

─── VALIDATION ───
  python -c "
import asyncio
from uuid import uuid4
from src.travel_engine.place_selector import PlaceCandidate, ScoredPlace
from src.travel_engine.route_optimizer import compute_legs_and_polylines, optimize_route

class Fake:
    async def travel_matrix(self, waypoints):
        from src.travel_engine.protocols import RouteLeg
        ids = [w[0] for w in waypoints]
        return [RouteLeg(from_place_id=a, to_place_id=b, duration_min=10, distance_km=1.0)
                for a in ids for b in ids if a != b]
    async def route_polyline(self, waypoints):
        return f'poly_{len(waypoints)}'

async def main():
    places = [ScoredPlace(place=PlaceCandidate(id=uuid4(), name=n, category='attraction',
              enriched_tags=[], lat=0.0, lng=0.0), score=1.0, score_breakdown={}) for n in ('A','B')]

    # Direct call — the shape P7's reorder will use
    legs, leg_polys, day_poly = await compute_legs_and_polylines(places, 0.0, 0.0, Fake())
    assert len(leg_polys) == 2 and day_poly == 'poly_3'

    # optimize_route still works after the refactor (regression check)
    result = await optimize_route(places, 0.0, 0.0, Fake())
    assert result.day_polyline == 'poly_3'
    assert len(result.leg_polylines) == 2

    print('PASS — 7.1 shared helper extracted and reused by optimize_route')

asyncio.run(main())
"

✅ Failure path: existing P4/P6 route_optimizer test suite still green after the refactor —
   run `python -m pytest tests/travel_engine/test_route_optimizer_polyline.py -v`.
```

---

## Step 7.2 — TripService edit operations

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Implement day-surgery service methods + schemas + exceptions, using the shared
compute_legs_and_polylines helper from 7.1, with the v2-locked dropped-stops and
reorder-morning-slot rules. This is step 7.2. No FastAPI routes yet (7.3). Wire
RoutingProvider via constructor default OsrmRoutingProvider() or an optional `routing=`
arg for tests. No new packages. No PlannerService / execute_tool / LLM.

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
      """404 — the referenced place_id is not on that day. LOCKED (v2): always 404,
      never 422 — this was ambiguous in v1."""
      def __init__(self, message: str = "stop not found on this day"):
          super().__init__(message, code="stop_not_found_on_day", status_code=404)

─── EXTEND src/trips/schemas.py ───

  class ReorderStopsIn(BaseModel):
      place_ids: list[uuid.UUID]   # full permutation of that day's stops

  class AddStopIn(BaseModel):
      place_id: uuid.UUID

─── EXTEND src/trips/repository.py (as needed) ───

  Flush-only helpers if missing:
  - delete TripPlace by (trip_id, place_id, day)
  - update order/times/polyline fields on existing rows
  - insert TripEditEvent   # TripRepository owns this write — see v2 ownership resolution below
  Keep soft-delete rules: TripPlace is hard-deleted (no SoftDeleteMixin).

─── EXTEND src/trips/service.py — private helpers ───

  def _hydrate_scored(trip_place) -> ScoredPlace:
      """PlaceCandidate from joined Place (to_shape -> lat/lng; category; name;
      enriched_tags list). score=1.0, score_breakdown={}."""

  def _snapshot_day(places_for_day) -> list[dict]:
      """
      {place_id, order_in_day, travel_time_min, visit_duration_min,
       suggested_start_time, polyline} per stop. LOCKED (v2): call this to capture
      'before' BEFORE any in-memory mutation begins — not after building the new plan.
      """

  async def _fixed_order_day(scored_in_requested_order, base_lat, base_lng, routing):
      """
      Reorder path — LOCKED (v2): calls the SHARED compute_legs_and_polylines(...) from
      step 7.1 directly. Does NOT permute. Does NOT reimplement any geometry logic —
      any duplication here is a regression, not an acceptable shortcut.
      """
      legs, leg_polylines, day_polyline = await compute_legs_and_polylines(
          scored_in_requested_order, base_lat, base_lng, routing,
      )
      return scored_in_requested_order, legs, leg_polylines, day_polyline

  async def _optimize_day(scored, base_lat, base_lng, routing) -> OptimizeResult:
      """Thin wrapper: await optimize_route(...) — which internally now also calls the
      SAME shared helper (step 7.1) for whichever order it picks."""
      return await optimize_route(scored, base_lat, base_lng, routing)

  def _day_plan_from_result(ordered, legs, leg_polylines, day_polyline) -> DayPlan:
      """
      LOCKED (v2): explicitly carries leg_polylines and day_polyline through onto the
      resulting stops/DayPlan — v1's version silently dropped these, which would have
      regressed GeoJSON on every edit even though the data was available.
        stops = build_day_schedule(ordered, legs)   # existing P4 function
        for stop, leg_polyline in zip(stops, leg_polylines):
            stop.leg_polyline = leg_polyline
        return DayPlan(stops=stops, total_travel_min=sum(l.duration_min for l in legs),
                        dropped_stops=[], day_polyline=day_polyline)
      """

  async def _validate_full_trip(trip, mutated_day_number, new_day_plan, *, edit_type) -> None:
      """
      Build TripItinerary for ALL days:
        - mutated_day_number uses new_day_plan (fresh, from this edit)
        - EVERY OTHER DAY is reconstructed ENTIRELY from already-persisted TripPlace
          fields — LOCKED (v2), zero new network/routing calls for unchanged days:
              total_travel_min = sum(stop.travel_time_min for stop in day_stops)
          This is the fix for v1's ambiguous "recompute lightly," which could have been
          read as re-running travel_matrix for every day on every edit.

      Call validate_trip(itinerary).

      LOCKED (v2) reorder-specific downgrade: if edit_type == EditType.REORDER and every
      remaining error after filtering is a morning-slot violation (identified by the
      "morning_slot_violation:" message prefix — see the trip_validator note below),
      move those into warnings instead of errors and proceed. Any OTHER error code, or
      any error at all for non-REORDER edit types, still raises TripEditValidationError.

      On unresolved errors: raise TripEditValidationError(details={
          "validation_errors": result.errors, "validation_warnings": result.warnings,
      })
      """

  NOTE on trip_validator: check_morning_slots (P4 file) should prefix its error strings
  with "morning_slot_violation: " if not already — a small, backward-compatible addition
  so this reclassification can filter reliably rather than fragile message-content matching.
  This does not change check_morning_slots' return type (still list[str]), only its string
  content, so no other P4/P5 caller needs to change.

  async def _persist_day_and_audit(
      self, trip, day_number, stops_to_persist, edit_type, before_snapshot, *, place_id=None,
  ) -> Trip:
      """
      UoW, single commit:
        1. Apply TripPlace mutations for day_number (delete + re-insert, or update in place —
           either is fine as long as it's atomic within this transaction).
        2. after_snapshot = _snapshot_day(stops_to_persist)
        3. TripRepository.insert_edit_event(trip_id=trip.id, edit_type=edit_type,
             day_number=day_number, place_id=place_id,
             payload={"before": before_snapshot, "after": after_snapshot})
           LOCKED (v2 — resolves the v1 self-contradiction): TripService/TripRepository is
           the SOLE creator of TripEditEvent. EvaluationService does NOT create this row —
           see step 7.5's narrowed mark_trip_edited.
        4. await EvaluationService(session).mark_trip_edited(trip.id)   # flag only, same UoW
        5. commit; return get_with_places(trip.id)
      """

─── PUBLIC METHODS ───

  async def reorder_stops(self, trip_id, day, place_ids, user_id, *, routing=None) -> Trip
  async def remove_stop(self, trip_id, day, place_id, user_id, *, routing=None) -> Trip
  async def add_stop(self, trip_id, day, place_id, user_id, *, routing=None) -> Trip
  async def reoptimize_day(self, trip_id, day, user_id, *, routing=None) -> Trip

  Common preamble:
    - load trip with places (404 if missing)
    - if trip.user_id != user_id: raise TripForbiddenError
    - resolve destination; base = _resolve_base(...)
    - before = _snapshot_day(current day's places)   # BEFORE any mutation (v2 explicit)

  reorder_stops:
    - LOCKED permutation check (v2, precise): raise TripEditValidationError unless
        len(place_ids) == len(current_day_place_ids) and set(place_ids) == set(current_day_place_ids)
      (catches missing IDs, extra IDs, AND duplicate IDs — v1's phrasing was ambiguous
      enough to miss the duplicate case if implemented naively)
    - order scored list by place_ids
    - _fixed_order_day (shared helper) → _day_plan_from_result → _validate_full_trip
      (edit_type=REORDER, so morning-slot downgrade applies) → _persist_day_and_audit
    - EditType.REORDER

  remove_stop:
    - if place not on that day → raise TripStopNotFoundError (v2 locked: always 404)
    - if len(day_stops) == 1 → TripEditValidationError(code="day_would_be_empty")
    - remaining → _optimize_day → if result.dropped_stops: should not normally happen for
      a pure removal (day only gets smaller), but if it somehow does, treat identically to
      add_stop's rule below (422, don't silently apply)
    - _day_plan_from_result → _validate_full_trip (edit_type=REMOVE_STOP, no downgrade) →
      _persist_day_and_audit
    - EditType.REMOVE_STOP; place_id set

  add_stop:
    - load Place; if missing → 404
    - if place.destination_id != trip.destination_id → 422
    - if place_id already on trip (any day) → TripStopConflictError 409
    - append hydrated place to day scored list → _optimize_day
    - LOCKED (v2 new rule): if result.dropped_stops is non-empty → raise
      TripEditValidationError(code="edit_would_drop_other_stops", details={
        "would_drop": [d.dict() for d in result.dropped_stops]}) — roll back, do NOT
      silently apply an add that requires removing something the user didn't ask about
    - _day_plan_from_result → _validate_full_trip (edit_type=ADD_STOP, no downgrade) →
      _persist_day_and_audit (insert new TripPlace)
    - EditType.ADD_STOP

  reoptimize_day:
    - current day scored → _optimize_day
    - LOCKED (v2): same dropped_stops check as add_stop — if the day's own stops can't fit
      without dropping one, that's a 422 telling the user which place is causing the
      problem, not a silent auto-removal
    - _day_plan_from_result → _validate_full_trip (edit_type=REOPTIMIZE_DAY, no downgrade) →
      _persist_day_and_audit
    - EditType.REOPTIMIZE_DAY

─── RULES ───
- Concurrency (v2, documented not implemented): no row-level locking in P7. Two concurrent
  edits to the same trip/day are last-write-wins. This is an explicit, accepted MVP
  limitation (forward lock F3) — state it in a code comment on TripService, not just here.
- validate_trip.errors (after any reorder-specific downgrade) → rollback, TripEditValidationError 422.
- OSRM fail → provider fallback (None polylines); still a 200-path result at HTTP layer.
- Never leave a half-updated day committed.
- Never call LLM / PlannerService / execute_tool.

─── DO NOT ───
- Register routes (7.3)
- Cross-day move endpoints
- Chat replan
- New tables
- Reimplement geometry logic outside compute_legs_and_polylines

✅ Validation:
  python -c "
from src.trips.service import TripService
for name in ('reorder_stops', 'remove_stop', 'add_stop', 'reoptimize_day'):
    assert hasattr(TripService, name)
print('PASS — 7.2 edit method surface')
"

  # pytest with FakeRoutingProvider (full cases land in 7.4):
  #   reorder preserves user order + polylines populated
  #   remove last stop → day_would_be_empty, 422
  #   add duplicate → 409
  #   add_stop that would trigger a drop → edit_would_drop_other_stops, 422, no mutation
  #   reorder with only morning-slot errors → 200, warnings present, commit happened
  #   remove/add/reoptimize with morning-slot errors → still 422 (no downgrade outside reorder)

✅ Failure path: injected validation failure → session rolled back; no TripEditEvent row.
✅ Failure path: add_stop forcing a drop → TripEditValidationError, zero TripPlace rows changed.
```

---

## Step 7.3 — trips/router.py edit endpoints

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Expose the four blueprint edit endpoints, with a user-keyed rate limit (v2 new) instead
of relying on the global default. This is step 7.3. Reuse TripService from 7.2. Return
ApiResponse[TripOut]. No new packages.

─── UPDATE src/config.py ───

  RATE_LIMIT_TRIP_EDIT_REQUESTS: int = 20
  RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS: int = 60
  # LOCKED (v2): edit routes get their OWN limit, not the global default — each edit call
  # can cost up to ~7 OSRM requests (compute_legs_and_polylines' N+1 calls), the same class
  # of "hammer a rate-limited external service" risk flagged for Nominatim in P2. Keyed by
  # authenticated user_id (these routes already require_auth) rather than IP — better than
  # IP-based limiting here, since it can't be evaded by switching networks, and a legitimate
  # multi-device user isn't penalized for using more than one IP.

─── IMPLEMENT src/trips/rate_limit.py (or inline in router.py) ───

  from src.core.middleware.rate_limit import get_rate_limiter
  from src.core.security.permissions import require_auth
  from src.core.security.jwt import TokenPayload
  from src.core.exceptions import RateLimitedError  # reuse existing 429 exception if present

  async def rate_limit_trip_edit(payload: TokenPayload = Depends(require_auth)) -> TokenPayload:
      """
      Route-level dependency — NOT a path-string middleware match (which can't cleanly
      handle the UUID segments in these paths). Reuses the SAME RateLimiterBackend
      Protocol/factory as the rest of the app; fail-open on backend errors, unchanged
      philosophy from P1/P6.
      """
      settings = get_settings()
      limiter = get_rate_limiter()
      key = f"{payload.user_id}:trip_edit"
      try:
          allowed, _ = await limiter.is_allowed(
              key, settings.RATE_LIMIT_TRIP_EDIT_REQUESTS, settings.RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS,
          )
      except Exception:
          return payload   # fail open — never block a legitimate edit because the limiter broke
      if not allowed:
          raise RateLimitedError(retry_after=settings.RATE_LIMIT_TRIP_EDIT_WINDOW_SECONDS)
      return payload

─── IMPLEMENT src/trips/router.py ───

  PATCH /{trip_id}/days/{day}/stops/reorder
    body: ReorderStopsIn
    Depends(rate_limit_trip_edit)   # implies require_auth via its own dependency
    → ApiResponse[TripOut]

  DELETE /{trip_id}/days/{day}/stops/{place_id}
    Depends(rate_limit_trip_edit)
    → ApiResponse[TripOut]

  POST /{trip_id}/days/{day}/stops
    body: AddStopIn
    Depends(rate_limit_trip_edit)
    → ApiResponse[TripOut]

  POST /{trip_id}/days/{day}/reoptimize
    Depends(rate_limit_trip_edit)
    → ApiResponse[TripOut]

  day: int path param (1-based day_number as stored on TripPlace).
  Pass payload.user_id into service. Map domain errors via existing exception handlers
  (TripStopNotFoundError → 404, TripEditValidationError → 422, TripStopConflictError → 409).

─── RULES ───
- Do NOT add these four paths to the global `_route_limit_table` — the dedicated
  route-level dependency above replaces that approach for this specific case (prefix
  matching for UUID paths remains a documented forward lock, not needed here since the
  dependency-based approach sidesteps the problem entirely).
- Router performs no DB / no travel_engine imports directly.

─── FAILURE BOUNDARY ───
- Unauthenticated → 401
- Non-owner → 403
- Rate limited → 429 with Retry-After
- Service validation → 422 ErrorResponse
- Conflict → 409
- Stop not found → 404

─── DO NOT ───
- optional_auth on edits
- Return raw dict
- Import redis / litellm

✅ Validation:
  - OpenAPI /docs lists four new routes
  - Manual or test client: owner reorder day 1 → 200 TripOut; times/polyline updated
  - GET /trips/{id}/geojson reflects new geometry when polylines present (regression
    check for the v2 polyline-carry-through fix)
  - Guest/unauth → 401; other user → 403
  - 21st rapid edit call from the same user within 60s → 429

✅ Failure path: add stop that overloads day → 422; DB trip unchanged (re-GET matches pre-edit)
```

---

## Step 7.4 — tests/trips/test_edit_replan.py

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Pytest coverage for P7 edit/replan, including regression tests for every v2 fix.
This is step 7.4. Use FakeRoutingProvider (deterministic matrix + polyline). Prefer
service-level tests + a thin HTTP test for auth matrix + rate limit.

─── CREATE tests/trips/test_edit_replan.py ───

  Required scenarios:
  1. reorder — order_in_day matches client permutation; suggested_start_time AND polyline
     updated (v2 regression for the polyline-carry-through fix)
  2. remove_stop — stop gone; remaining re-routed
  3. remove last stop on day — 422 day_would_be_empty; unchanged
  4. remove a place_id not on that day — 404 stop_not_found_on_day (v2 regression, was
     ambiguous "404 or 422" in v1)
  5. add_stop — new TripPlace; optimize ran; polyline populated
  6. add duplicate place — 409
  7. add wrong destination — 422
  8. add_stop that forces optimize_route to drop another stop — 422
     edit_would_drop_other_stops, details list the would-be-dropped place, ZERO TripPlace
     rows changed (v2 regression — this was a silent side-effect in v1)
  9. reoptimize_day — succeeds with Fake routing
 10. reoptimize_day that forces a drop — same 422 as add_stop's case
 11. ownership — wrong user_id → TripForbiddenError / HTTP 403
 12. OSRM fallback — Fake that returns fallback / None polyline → still success (no 500)
 13. reorder with ONLY morning-slot validation errors → 200, warnings present, commit
     happened, TripPlace order actually matches the user's requested order (v2 regression)
 14. remove/add/reoptimize with morning-slot errors present → still 422, no downgrade
     (v2 regression — the downgrade is reorder-only)
 15. reorder submitting a duplicate ID (e.g. [A, A, B] for a day that has [A, B, C]) → 422
     (v2 regression for the precise len+set permutation check)
 16. successful edit → TripEditEvent row with correct EditType + payload before/after,
     created exactly once (v2 regression — proves the v1 double-insert/missing-insert risk
     is resolved: assert TripEditEvent count increases by exactly 1, not 0 or 2)
 17. validation failure → rollback; count TripEditEvent before/after failed add — unchanged
 18. unchanged days cost zero additional routing calls during a single-day edit — spy on
     FakeRoutingProvider.travel_matrix / route_polyline call counts and assert they only
     reflect the ONE mutated day, not all days on the trip (v2 regression for the
     "recompute lightly" ambiguity fix)
 19. rate limit — 21st edit call within the window from the same user → 429 (mock the
     limiter backend, don't rely on real timing in unit tests)

─── FAILURE BOUNDARY ───

  Tests must not require live OSRM or LLM.
  DB: use wandr_test / existing fixtures pattern from tests/trips/.

─── DO NOT ───

  - Hit real OSRM in CI unit tests
  - Skip ownership, rollback, or the v2 regression cases above

✅ Validation:
  python -m pytest tests/trips/test_edit_replan.py -v  → green
  Full suite still green: python -m pytest tests/ -v

✅ Failure path: test asserts rollback — count TripEditEvent before/after failed add
```

---

## Step 7.5 — EvaluationService.mark_trip_edited (narrowed — v2)

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Honor AGENT.md — evaluation reflects every edit. This is step 7.5.
LOCKED (v2): this step does NOT create TripEditEvent — TripService (step 7.2) already owns
that write, in its own UoW, resolving the v1 self-contradiction. This step is now a narrow,
purely additive flag-setter.

─── EXTEND src/evaluation/repository.py ───

  async def get_latest_for_trip(self, trip_id: UUID) -> TripEvaluation | None: ...
  async def mark_user_edited(self, evaluation: TripEvaluation) -> TripEvaluation:
      # set user_edited=True; flush only
      ...

─── EXTEND src/evaluation/service.py ───

  async def mark_trip_edited(self, trip_id: UUID) -> None:
      """
      LOCKED (v2, resolves the v1 contradiction): this method does NOT create a
      TripEditEvent — TripService already did, in the same transaction, before calling
      this. This method ONLY looks up the latest TripEvaluation for trip_id and sets
      user_edited=True if one exists. No evaluation row → no-op, not an error.
      No LLM. No planner.
      """
      evaluation = await self.repo.get_latest_for_trip(trip_id)
      if evaluation is not None and not evaluation.user_edited:
          await self.repo.mark_user_edited(evaluation)

  # Renamed from the v1 draft's `record_edit` — that name implied event-creation
  # responsibility this method deliberately does NOT have. `mark_trip_edited` is
  # unambiguous about what it actually does.

─── CONFIRM WIRING IN TripService (already specified in step 7.2's _persist_day_and_audit) ───

  TripService inserts TripEditEvent directly via TripRepository, THEN calls
  EvaluationService(session).mark_trip_edited(trip.id) — same session, same transaction,
  before commit. If step 7.2 was implemented before this step landed, verify it already
  calls this method under its final name; rename any placeholder call if needed.

─── FAILURE BOUNDARY ───

  - No evaluation row → mark_trip_edited no-ops; edit still succeeds
  - Keep the flag update in-UoW (same transaction as the TripPlace mutation and the
    TripEditEvent insert) so a rollback covers all three consistently — do not make this a
    post-commit best-effort call

─── DO NOT ───

  - Create TripEditEvent here (that's TripService's job, per step 7.2 — this is the
    explicit fix for the v1 contradiction)
  - New TripEvaluation columns / migrations
  - Evaluation HTTP routes
  - Skip the flag update on a successful edit when an evaluation row exists

✅ Validation:
  - Edit trip with existing evaluation → user_edited becomes True
  - Edit trip without evaluation → TripEditEvent still exists (created by TripService);
    HTTP 200; mark_trip_edited no-ops cleanly
  - Assert EvaluationService.mark_trip_edited does NOT insert into trip_edit_events table
    (a direct regression test for the v1 ownership contradiction — spy on the repository's
    insert method and assert zero calls from within mark_trip_edited)

✅ Failure path: missing evaluation does not block edit; does not raise
```

---

## Step 7.6 — Smoke + context.md ship

```
Read AGENT.md and docs/context.md before proceeding.

TASK: Close P7 documentation checkpoint. Optional live smoke. This is step 7.6.
Only mark context.md after pytest (and smoke if present) are green.

─── OPTIONAL scripts/test_p7_smoke.py ───

  If written: seed or use existing trip owned by a test user; reorder day 1;
  assert TripEditEvent (created exactly once); assert GeoJSON shows the new polyline;
  print a GeoJSON snippet. Keep offline-capable with Fake where possible; live OSRM
  optional behind an env flag (same spirit as P4/P6).

─── UPDATE docs/context.md ───

  - Last updated = today; Next step = post-P7 / production readiness (per blueprint)
  - Progress: 7.0–7.6 ✅
  - Current state one-liner: P7 done — trip day edit/replan HTTP + TripEditEvent, geometry
    computation shared between generation and edit paths
  - Implemented modules: compute_legs_and_polylines (shared), edit methods, routes,
    rate_limit_trip_edit, EvaluationService.mark_trip_edited
  - Live endpoints: four edit rows
  - Known MVP limitation (state explicitly, per v2 Decision Log #22): no row-level locking
    on concurrent edits to the same trip — last-write-wins
  - Stubs only: remove "P7 trip edit/replan HTTP still stubs"
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

## P7 ship criteria (v2)

| Check | Expected |
|-------|----------|
| Base prefs | `save_from_state` stores `base_lat`/`base_lng` when present on state |
| Resolve base | prefs win; else Destination |
| Shared geometry helper | `compute_legs_and_polylines` used by BOTH `optimize_route` and reorder — no duplicated logic |
| Reorder | User order preserved; times + polylines refreshed; no permutation search |
| Remove / add / reoptimize | `optimize_route` path; TripOut returned; polylines carried through to persisted rows |
| Dropped-stops on add/reoptimize | 422, not a silent extra mutation |
| Empty day | 422; unchanged |
| Duplicate/malformed reorder list | 422 via exact `len`+`set` permutation check |
| Stop not found on day | 404, never 422 |
| Validation errors | 422 + rollback; no audit row — EXCEPT reorder's morning-slot-only case, which is 200 with warnings |
| Unchanged days | Zero additional routing/network calls during a single-day edit |
| OSRM fallback | 200 not 500 |
| Auth + rate limit | require_auth; non-owner 403; guest cannot edit; user-keyed 429 after threshold |
| Audit | Exactly one `TripEditEvent` per success, created by `TripService`; `user_edited` set via `EvaluationService.mark_trip_edited` (flag only) |
| Layering | No PlannerService / execute_tool / LLM / litellm / langgraph on edit path |
| Envelope | `ApiResponse[TripOut]` |
| GeoJSON | Reflects post-edit polylines without a new endpoint |
| Concurrency | Documented MVP limitation, not silently absent |
| pytest | `test_edit_replan` (including all v2 regression cases) + full suite green |
| context.md | Updated only on 7.6 after green |

---

## Recommended OpenSpec implementation batches

After P6.5 is green, apply as **separate** implementation changes, in order:

1. `7.0` — base coords on preferences + `_resolve_base`
2. `7.1` — extract `compute_legs_and_polylines`, refactor `optimize_route` to use it
3. `7.2` — TripService edit ops + schemas + exceptions (TripService owns `TripEditEvent`)
4. `7.3` — four router endpoints + `rate_limit_trip_edit`
5. `7.4` — `tests/trips/test_edit_replan.py` (including all v2 regression cases)
6. `7.5` — `EvaluationService.mark_trip_edited` (flag only, no event creation)
7. `7.6` — smoke (optional) + `docs/context.md`

Do **not** open a full propose→archive cycle for each micro-detail inside a step unless a
design conflict appears.