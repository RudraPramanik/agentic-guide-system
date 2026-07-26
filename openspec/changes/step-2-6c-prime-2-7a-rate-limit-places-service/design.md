## Context

P2.5+2.6c are done: OSRM `get_route` and public `GET /api/v1/destinations/search` work. `_resolve_limits` still only special-cases the planner path via `startswith`; destinations search inherits the default 60/min. `src/places/schemas.py` and `src/places/service.py` are still step-0.1 stubs. Canonical next pair from `docs/steps/step2.md`: **2.6c′** (path table + 20/min on search) then **2.7a** (PlaceOut + PlaceService). HTTP for places stays **2.7b**.

## Goals / Non-Goals

**Goals:**
- Settings-driven ordered route-limit table; destinations search exact path → 20/60; planner 10/60 unchanged; other paths → default
- Fail-open and P1 middleware tests unchanged in behavior
- `PlaceOut` with lat/lng from geometry; `PlaceService.list_by_destination` / `get_by_id`
- Mandatory destination existence check → `DestinationNotFoundError` (404), never silent empty page
- Update `docs/context.md` → Next **2.7b**

**Non-Goals:**
- Places HTTP router / `main.py` registration (2.7b)
- `compute_readiness` (2.8), P2 pytest modules (2.9)
- Redis rate limiter (P6)
- Changing destinations search business logic

## Decisions

### D1 — Exact-match route table (per step 2.6c′)
- Replace planner-only `startswith` branch with `_route_limit_table()` → list of `(path, limit, window)` from `get_settings()`
- Lookup: `path == route_path` (exact); first match wins; else default
- Alternative considered: keep `startswith` for planner — rejected; step locks exact match and table generalization

### D2 — Config owns all path strings
- Add `RATE_LIMIT_DESTINATIONS_SEARCH_REQUESTS=20`, `_WINDOW_SECONDS=60`, `_PATH=/api/v1/destinations/search`
- Mirror into `.env.example`; no hardcoded routes in middleware

### D3 — PlaceService raises `DestinationNotFoundError`, not bare `NotFoundError`
- Step text says `dest_repo.get_by_id_or_raise` “raises DestinationNotFoundError”, but `BaseRepository.get_by_id_or_raise` raises generic `NotFoundError`
- Implement existence check like `DestinationService.get_by_id`: `get_by_id` → if None raise `DestinationNotFoundError(destination_id=...)`
- Validation script in step 2.7a catches `DestinationNotFoundError` specifically — must match
- Alternative considered: override `get_by_id_or_raise` on `DestinationRepository` — deferred; service-layer wrap is consistent with existing destination service

### D4 — PlaceOut.from_place via geoalchemy2.shape.to_shape
- `.y` → lat, `.x` → lng; `from_attributes` for other columns
- No new packages (geoalchemy2 already in stack)

### D5 — Bundle order in implementation
- Land 2.6c′ (config + middleware) and validate `_resolve_limits` first
- Then 2.7a (schemas + service) and validate against seeded Darjeeling
- Context bump only after both gates pass

## Risks / Trade-offs

- **[Risk]** Exact-match changes planner matching vs old `startswith` → **Mitigation:** planner path is the full generate path; existing tests use that exact path; run `tests/core/test_middleware.py`
- **[Risk]** Step doc `get_by_id_or_raise` wording mismatches BaseRepository → **Mitigation:** D3; do not invent DestinationRepository override in this change
- **[Risk]** 2.7a validation needs seeded Darjeeling → **Mitigation:** document seed prerequisite in tasks; fail clearly if empty
- **[Trade-off]** Bundling skips shipping rate limit alone → acceptable; 2.6c′ is tiny and both are sequential

## Migration Plan

- Config defaults are additive; no DB migration
- Deploy: restart uvicorn after `.env` / settings pick-up
- Rollback: revert middleware to planner-only branch and remove new settings (search falls back to 60/min)

## Open Questions

- None blocking. Optional later: whether DestinationRepository should override `get_by_id_or_raise` for domain exception consistency (out of scope here).
