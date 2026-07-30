## Context

P0–P3 are done: DB/auth, geo seed, enrichment, Qdrant index, readiness with live `search_available`. `src/travel_engine/` and planner tools remain stubs. Blueprint v6 (`docs/blueprint_final.md`) defines P4 as the pure-Python intelligence layer; pre-flight addendum (`docs/blueprint.md`) corrects vocabulary bugs and locks underspecified algorithms before P5 wraps this layer in tools.

Constraints (AGENT.md): travel_engine has **no** LLM, network, or DB; routing via injected `RoutingProvider`; geo only through `src/geo/` (outside travel_engine); all env via `get_settings()`.

## Goals / Non-Goals

**Goals:**

- Ship a complete, unit-testable travel engine (4.1–4.7) with corrected category/interest vocabularies.
- Inject routing via protocol + `OsrmRoutingProvider` stub (4.8) without polluting travel_engine with `geo/` imports.
- Emit data shapes P5/P6 need: `dropped_stops`, explain strings for `tool_trace`.
- Add CORS so a separate frontend can call the API with credentials.
- Produce `docs/steps/step4.md` as the build prompt incorporating addendum LOCKED items.

**Non-Goals:**

- LangGraph agent loop, tool implementations beyond stub envelope, SSE, trip CRUD, evaluation recording.
- Redis-backed rate limits / geocoder cache (P6 TODO).
- Changing auth cookie SameSite code (decision recorded only).
- Patching every line of `blueprint_final.md` in this change (recommend follow-up doc sync).

## Decisions

### D1 — Vocabulary split (supersedes blueprint_final travel_rules draft)

**Choice:** Structural constants keyed by `Place.category` (P2 locked: `museum|viewpoint|monastery|attraction|park|trailhead`). Interest weights keyed by `Place.enriched_tags` membership (P3 `PLACE_TAG_VOCAB`).

**Why:** v6 draft mixed them — `VISIT_DURATION` had `trek`/`cultural` (never equal `place.category`) and missed `attraction`/`trailhead`; `MORNING_ONLY` had dead `sunrise_point`.

**Alt considered:** Single unified taxonomy — rejected; would require re-seeding P2 and re-enriching P3.

### D2 — Scoring = sum of matching interest weights

```
score = sum(CATEGORY_WEIGHTS[tag] for tag in place.enriched_tags
            if tag in CATEGORY_WEIGHTS and tag in user_interests)
```

**Why:** Multi-interest places must outrank single-interest matches; max/average would hide that.

**Duration lookup:** always `.get(category, VISIT_DURATION_DEFAULT_MIN)`.

### D3 — Route ordering = brute-force permutations

With `MAX_PLACES_PER_DAY = 6`, evaluate all orderings of day stops (fixed start at `base_lat`/`base_lng`) via `routing.travel_matrix()`, pick min total travel. Cap 720 — deterministic, no `python-tsp`.

**Alt:** nearest-neighbor heuristic — rejected for non-determinism and harder testing at this scale.

### D4 — Drop-retry records `dropped_stops`

When travel > `MAX_DAILY_TRAVEL_MIN`, drop lowest-scored stop (max 3 attempts). Output includes `dropped_stops: list[{place_id|name, reason}]` so P5 REPLAN prefers `expand_poi_search` over further thinning when already dropped.

### D5 — `explain_selection` → trace-shaped strings, not TripEvaluation column

Return compact explanation strings from selector (top-N ready for `rank_places` ToolResult). Avoids schema migration for observability data already covered by `tool_trace` JSONB (P5/P6).

### D6 — Protocols stay in travel_engine; OSRM adapter in planner

`RoutingProvider` + `RouteLeg` in `travel_engine/protocols.py`. `OsrmRoutingProvider` in `planner/routing_provider.py` wraps `geo/osrm.py`, maps haversine fallback → `used_fallback` on legs / caller flag.

### D7 — CORS now; SameSite Option A for MVP

`CORSMiddleware` with `CORS_ALLOWED_ORIGINS` list + `allow_credentials=True` (never `*`). Cookie policy: same registrable domain → keep `SameSite=Lax` (documented in context.md). Cross-site Option B deferred.

### D8 — Day times are wall-clock naive strings

`DAY_START_TIME` etc. are destination-local wall-clock; do not attach timezone or convert to UTC in travel_engine (addendum B).

### D9 — Forward locks for P5/P6 (design-only here)

| ID | Lock | Lands in |
|----|------|----------|
| F1 | `ToolContext` (db, routing) NOT in LangGraph `TravelState` | 5.6 |
| F2 | Prefer session-per-DB-tool over one session for 45s generation | 5.1–5.3 |
| F3 | SSE = queue + background graph task, not await-then-dump | 6.2 |
| F4 | Client disconnect cancels graph task | 6.2 |
| F5 | `PLANNER_ABSOLUTE_MIN_PLACES` hard floor before graph | 6.2 |
| F6 | Cache key includes `round(base_lat/lng, 3)` | 6.4 |
| F7 | Guest ownership = `wandr_session` == `Trip.session_id` | 6.1/6.3 |
| F8 | Agent no-tool: nudge + `tool_choice=required` once, then default tool | 5.9 |

## Module map (P4)

```
src/travel_engine/
  protocols.py          # RoutingProvider, RouteLeg (+ TravelTimeMatrix if needed)
  travel_rules.py       # corrected constants (D1)
  place_selector.py     # select_places, explain_selection
  day_allocator.py      # allocate_days
  route_optimizer.py    # optimize_route → OrderedStop + dropped_stops
  schedule_builder.py   # build_day_schedule
  trip_validator.py     # validate_trip → ValidationResult
src/planner/
  routing_provider.py   # OsrmRoutingProvider
  tools/                # ToolResult envelope + execute_tool skeleton (stub)
src/config.py           # CORS_ALLOWED_ORIGINS
src/main.py             # CORSMiddleware
```

## Resilience (P4 scope)

- travel_engine: no external I/O — failures are domain ValidationResult / empty scores, not HTTP.
- `OsrmRoutingProvider`: inherits `geo/osrm.py` contract (tenacity 2x → haversine × 1.4); never raises 500 to caller; surfaces `used_fallback`.
- Fake provider in unit tests — zero network.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| blueprint_final still shows buggy rules → agent follows wrong draft | step4.md + this design are SoT; cite docs/blueprint.md §B; follow-up patch blueprint_final |
| Permutation TSP with async matrix N! calls | Batch matrix once for all waypoint pairs if provider supports; or sync Fake in tests; keep N≤6 |
| Places with empty `enriched_tags` score 0 | Still allocatable via fallback / budget filters; document; P5 search should prefer enriched places |
| CORS misconfig blocks local Next.js | Default origins include `http://localhost:3000` in settings example; never ship `*` with credentials |
| Drop-retry removes only anchor → VALIDATE fails | `dropped_stops` + P5 prompt guidance; validator still reports missing anchor |

## Migration Plan

1. Land CORS + settings (safe additive).
2. Implement travel_engine modules bottom-up: protocols → rules → selector → allocator → optimizer → schedule → validator.
3. Wire OsrmRoutingProvider + tool stub.
4. pytest suite; update context.md after proofs pass.
5. Rollback: revert module files; CORS env empty list = deny all cross-origin (safe default if unset carefully — prefer explicit empty = no origins).

## Open Questions

1. Should `TravelTimeMatrix` be a concrete type or is `list[RouteLeg]` enough? **Default:** `list[RouteLeg]` + optional helper; add matrix type only if optimizer needs pair lookup API.
2. Budget filter semantics in place_selector (P4.3) — blueprint says "filter by budget" but no per-place cost field exists yet. **Default for P4:** treat budget as soft preference flag on preferences object; no hard exclude until a cost field exists (document in step4).
3. Geographic coherence threshold in trip_validator — exact numeric threshold not in blueprint. **Default:** use a named constant in travel_rules (e.g. max std-dev km) tunable in one place.
