## Context

See proposal.md — Why. Live generate injects `OsrmRoutingProvider()` into `ToolContext` (`src/planner/service.py`) and `TripService` (`src/trips/service.py`). That adapter fans out pairwise `geo.osrm.get_route` to public `OSRM_BASE_URL`. `optimize_route` then calls `populate_leg_polylines` (N+1 extra `/route` calls). Skipping geometry alone leaves the matrix; the 45s ceiling still loses. `RoutingProvider` already exists; GeoJSON already emits Points when polylines are `None`. `write_narrative` already owns prose without mutating stops — the Layla-shaped guidebook later attaches there, not in routing.

Constraints: AGENT.md (geo only via `src/geo/`; `travel_engine` pure; env via `get_settings()`; SSE `wait_for` unchanged). No self-hosted OSRM. No new HTTP endpoints.

## Goals / Non-Goals

**Goals:**

- Default generate/edit routing completes in-process so a typical Darjeeling tool loop fits inside 45s.
- Keep one swap point for a later paid/self-host OSRM (`ROUTING_BACKEND=osrm`).
- Leave schedule/TripPlace/GeoJSON shapes unchanged so maps and Layla export can light up later without a graph rewrite.

**Non-Goals:**

- Changing permutation/drop-retry in `travel_engine.route_optimizer`.
- OSRM `/table`, new routing vendors, LLM/model swap, FE abort wiring, guidebook PDF.

## Decisions

### 1. Haversine provider, not “skip polyline in optimizer”

**Choice:** New `HaversineRoutingProvider` + factory. `optimize_route` still calls `route_polyline`; the haversine adapter returns `None` immediately (already specified as valid).

**Why:** The budget killer is `travel_matrix` (42 public `/route` calls/day), not N+1 polylines. Leaving `travel_engine` untouched preserves P6/P7 polyline contracts.

**Alternatives considered:**

- Skip `populate_leg_polylines` only → rejected (matrix still >45s).
- Public OSRM `/table` → rejected (still depends on demo SLA; `/route` spec lock; paid URL later is the real accuracy path).
- Bigger LLM / raise 45s → rejected (does not remove HTTP).

### 2. Public `estimate_route` in `geo/osrm.py`

**Choice:** Lift today’s `_fallback_route` math to a public helper that never HTTP-calls. `get_route` keeps trying live OSRM then reuses the helper on miss. Haversine provider calls the helper only.

**Why:** AGENT.md: geo math/HTTP stay in `src/geo/`. Must not use `get_route` for the fast path (it hits public OSRM first, including 10s read timeouts).

**Alternatives considered:** Duplicate haversine in `planner/` → rejected (geo leakage). Flag on `OsrmRoutingProvider` to skip HTTP → rejected (mixes two backends in one class; factory is clearer for a later paid adapter).

### 3. `ROUTING_BACKEND` default `haversine`

**Choice:** Same pattern as `PLACES_EMBEDDING_BACKEND`. Default `haversine` so local and current VPS honor 45s without a public demo. `osrm` keeps `OsrmRoutingProvider` + `OSRM_BASE_URL`. Unknown value → haversine (fail-soft).

**Why:** Operators cannot self-host now; paid URL is a settings flip, not a graph change.

**Alternatives considered:** Infer haversine when URL is `router.project-osrm.org` → rejected (magic). Default `osrm` → rejected (reproduces tonight’s timeout).

### 4. One factory for generate and P7 edits

**Choice:** `PlannerService.generate` and `TripService.__init__` default to `get_routing_provider()`. Tests keep injecting Fake.

**Why:** Same times on generate and day-edit; no second code path.

### 5. Do not change the 12-tool graph

**Choice:** Keep search → rank → route → schedule → validate → optional REPLAN/`expand_poi_search`. Fast matrix makes expand cheap; Layla later still uses the same schedule + `write_narrative` bookend.

**Why:** Smallest change that hits 45s; guidebook is content on saved trips, not routing.

## Risks / Trade-offs

- [Hill-road times underestimated] → Haversine × 1.4 can overpack Darjeeling days vs real winding roads. Accept for MVP; `used_fallback=True` is honest; later `ROUTING_BACKEND=osrm` restores road times without schema change.
- [Validators fail more if times are too low] → If `MAX_DAILY_TRAVEL_MIN` still trips, REPLAN/expand stays; it is cheap under haversine. If overpack is a product issue, tighten caps in a later change — not this one.
- [Specs named `OsrmRoutingProvider()` as production default] → Delta specs replace that with the factory; keep the OSRM class for the `osrm` backend.
- [FE map looks sparse] → Point-only GeoJSON is already specified; user accepted no polylines for this version.

## Migration Plan

1. Implement helper + provider + factory + settings; wire generate and TripService.
2. Unit tests: estimate (no HTTP), haversine matrix + None polylines, factory selection, generate/TripService defaults.
3. Live proof: Darjeeling `POST /api/v1/planner/generate` under default 45s → `itinerary_done` + `trip_id`.
4. Document `ROUTING_BACKEND` in `.env.example` and `docs/context.md` after validate.
5. Rollback: set `ROUTING_BACKEND=osrm` or revert the factory default.

## Open Questions

- None blocking. Paid vendor (Google/Mapbox vs self-host OSRM) is a future adapter behind the same factory.
