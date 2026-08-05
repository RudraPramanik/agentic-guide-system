## ADDED Requirements

### Requirement: Manual refresh after P6 phase completion

After P6 is recorded complete in `docs/context.md` (Progress 6.0–6.5 ✅, next step P7.1), the developer manual MUST be refreshed in the same docs-sync change (or immediately after). The index `docs/app/documentation.md` MUST set **Through step** to at least **P6.5**, bump **Last refreshed**, and update the snapshot so it no longer claims trips HTTP CRUD/GeoJSON/claim, `POST /api/v1/planner/generate`, route polylines, Redis/InMemory rate limiter + planner cache backends, or `scripts/test_p6_smoke.py` are unbuilt (when those rows are ✅ in context). The refresh MUST also clear any residual “next = P5.12 / planner HTTP later” framing left from the P5.11 marker. The maintenance refresh log MUST record a phase-complete (or deferred catch-up) row covering through P6.5. If context has not yet marked all P6 steps ✅, Through step MUST NOT exceed the highest validated P6 (or residual P5) step in context.

#### Scenario: Index reflects P6 complete

- **WHEN** a developer opens `docs/app/documentation.md` after this refresh with context showing P6.5 done
- **THEN** the header shows Through step ≥ P6.5 and the snapshot lists planner SSE generate, trips HTTP + GeoJSON/claim, cache backends, and P6 verification artifacts as present, with next product work described as P7.1 (not “build P6”)

#### Scenario: Maintenance log records the catch-up

- **WHEN** the refresh is finished for P6.5
- **THEN** `docs/manual/06-maintenance.md` includes a refresh-log row for Through step P6.5 (or equivalent) with trigger noting P6 phase complete (or P5+P6 catch-up)

#### Scenario: Through-step does not overshoot context

- **WHEN** `docs/context.md` still lists an incomplete P6 step as Next
- **THEN** the manual Through step stays ≤ the highest ✅ step and does not claim unfinished modules as shipped

### Requirement: Module map and wiring include P6 artifacts

The module map and imports/wiring pages MUST list as real (not stub) whatever `docs/context.md` marks implemented for P6, including at minimum when ✅: `route_polyline` / schedule polylines, `trips` exceptions/schemas/repo/service (`save_from_state`, ownership, claim), trips HTTP CRUD + GeoJSON + claim router, planner schemas + SSE `/generate` (floor 409, terminal buffer → persist, proxy headers), `CacheBackend` + `InMemoryCacheBackend` / `RedisCacheBackend` + `get_cache_backend()`, Redis/InMemory rate limiter selection on `REDIS_URL`, planner MVP cache helpers, `tests/trips/` / cache/rate-limit/SSE tests as applicable, and `scripts/test_p6_smoke.py`. Residual P5 gaps still marked stub in the manual (PlannerService bridge, tool-loop tests, agent smoke) MUST be marked real when context says ✅. Stub callouts MUST remain only for packages still stubbed in `docs/context.md` (P7 trip edit/replan HTTP, evaluation HTTP, `auth/dependencies.py`, and any deferred clarification-path evaluation note).

#### Scenario: Junior looks up trips HTTP

- **WHEN** a developer opens the module map looking for `trips/router.py` after context marks 6.3 ✅
- **THEN** they see list/get/delete/geojson/claim as real with ownership/auth notes, not as “HTTP stubs”

#### Scenario: Junior looks up planner generate

- **WHEN** a developer opens the module map looking for `planner/router.py` after context marks 6.2 ✅
- **THEN** they see `POST /api/v1/planner/generate` SSE as real (registered), not as “lands in P6”

#### Scenario: Junior looks up cache backends

- **WHEN** a developer opens the module map looking for `core/cache/backends.py` after context marks 6.4 ✅
- **THEN** they see `CacheBackend` + Redis/InMemory implementations and rate-limiter backend selection as real

### Requirement: How-to-change recipes cover P6 verification and SSE paths

Recipes MUST mention running `python scripts/test_p6_smoke.py` (when context marks 6.5 ✅) and relevant pytest packages (`tests/trips`, cache backends, rate limiter, planner SSE) where appropriate. Recipes that mention planner generate MUST note: reverse-proxy buffering off for the SSE path, frontend `fetch()` + manual SSE parsing (not `EventSource`), optional `wandr_session` cookie, and that empty `REDIS_URL` keeps rate limit + planner cache in-memory (not shared across workers). Recipes MUST NOT present P7 edit/replan endpoints as live.

#### Scenario: Smoke recipe after P6

- **WHEN** a developer follows verification recipes after the P6 refresh
- **THEN** they are directed to the P6 smoke script and trips/planner/cache pytest packages consistent with `docs/context.md`

#### Scenario: SSE client guidance is present

- **WHEN** a developer reads how-to-change guidance for calling planner generate
- **THEN** they learn to use POST `fetch()` (not `EventSource`) and that proxies must disable response buffering for that path

#### Scenario: No invented P7 edit routes

- **WHEN** a developer reads how-to-change or live-endpoint guidance after P6
- **THEN** they do not find trip edit/replan HTTP presented as registered live routes

### Requirement: Architecture docs light-touch after P6

`docs/app/system.md` and `docs/app/lld.md` MUST NOT retain factual claims that contradict post-P6 `docs/context.md` (e.g. trips “HTTP CRUD later”, planner “HTTP generate P6” as future-only, Cache-Aside “planner cache later”). Corrections MUST be minimal status/framing fixes — not architecture rewrites. Residual stubs (P7 edit/replan, evaluation HTTP) MAY remain called out as future work.

#### Scenario: system.md trips and planner rows match reality

- **WHEN** a reader checks the `src/trips/` and `src/planner/` summaries in `system.md` after P6 is complete in context
- **THEN** the rows no longer claim trips HTTP or planner generate are only future work; P7 edit/replan may still be noted as next

#### Scenario: lld.md pattern table marks shipped P6 patterns

- **WHEN** a reader checks the pattern catalog in `lld.md` for Cache-Aside / rate-limiter backend Strategy after P6 complete
- **THEN** planner cache and Redis/InMemory selection are framed as shipped (or present), not as upcoming-only work

## MODIFIED Requirements

### Requirement: Module map with real vs stub

The manual MUST include a module/package map keyed to the repository layout, listing key files and responsibilities for implemented modules through the current “through step” marker, and MUST mark stub-only packages so juniors do not assume public APIs exist. After the P6 catch-up refresh, the through-step marker MUST be at least P6.5 when context records P6 complete, and MUST treat geo gateways, destinations/places HTTP, readiness (including live `search_available`), P3 search/enrich/index, CORS, full `travel_engine/*`, planner routing provider, full P5 tools + orchestration + graph + PlannerService SSE bridge + P5 verification artifacts, and full P6 trips HTTP + planner SSE generate + cache backends + polylines + P6 verification artifacts as real (when ✅ in context). Stub callouts MUST match `docs/context.md` (P7 trip edit/replan HTTP; evaluation HTTP; `auth/dependencies.py`; any still-deferred clarification evaluation).

#### Scenario: Stub packages are explicit

- **WHEN** a developer looks up P7 trip edit/replan or evaluation HTTP while those remain unbuilt
- **THEN** the manual states they are not implemented / not registered without inventing public APIs

#### Scenario: Real geo modules are listed

- **WHEN** the “through step” is at least P2.2
- **THEN** `src/geo/geocoder.py` and `src/geo/overpass.py` appear as real gateways with their public entry points (`geocode`, `fetch_pois`)

#### Scenario: P2 verification modules are listed as real

- **WHEN** the “through step” is at least P2.10
- **THEN** `src/geo/osrm.py`, destinations/places routers and readiness, P2 pytest packages, and `scripts/test_p2_smoke.py` appear as real

#### Scenario: P3 and P4 modules are listed as real

- **WHEN** the “through step” is at least P4.10
- **THEN** `src/search/*`, enrich/index scripts, `src/travel_engine/*`, `OsrmRoutingProvider`, and `scripts/test_p4_smoke.py` appear as real

#### Scenario: P5 planner modules are listed as real

- **WHEN** the “through step” is at least P5.14 (and context marks those steps ✅)
- **THEN** planner tools/orchestration/graph nodes/builder, evaluation generation persist, PlannerService bridge, tool-loop tests, and `scripts/test_agent.py` appear as real

#### Scenario: P6 persistence and SSE modules are listed as real

- **WHEN** the “through step” is at least P6.5 (and context marks those steps ✅)
- **THEN** trips HTTP CRUD/GeoJSON/claim, `POST /api/v1/planner/generate`, cache backends, rate-limiter Redis/InMemory selection, route polylines, and `scripts/test_p6_smoke.py` appear as real
