## Context

P7.0–7.2 are done and archived: base prefs + `_resolve_base`, shared `populate_leg_polylines`, TripService day surgery with preserve-order schedule, edit exceptions/schemas, Fake service tests, thin `mark_trip_edited`. `docs/context.md` Next = **7.3**.

Step **7.3** (`docs/steps/step7.md`) exposes the four blueprint edit endpoints over HTTP with a user-keyed rate-limit dependency. Blueprint product table (paths/bodies/`ApiResponse[TripOut]`/`require_auth`+ownership) is authoritative for the surface; step7 locks intentional deltas: user-keyed `rate_limit_trip_edit` (not UUID path-table rows), Router→Service only, no planner/LLM.

Today: `trips/router.py` has CRUD + GeoJSON + claim only; `RATE_LIMIT_TRIP_EDIT_*` missing; `get_rate_limiter()` exists (InMemory/Redis); middleware returns 429 inline without a `RateLimitedError` type; no `rate_limit_trip_edit` dependency.

Constraints: AGENT.md; zero new packages; fail-open limiter; dual IP middleware default OK; no DB/travel_engine imports in router.

## Goals / Non-Goals

**Goals:**

- Four edit routes registered and OpenAPI-visible.
- Auth matrix: `require_auth` + owner + `rate_limit_trip_edit` → 401 / 403 / 429 as locked.
- Settings-driven edit rate limits; dependency uses `get_rate_limiter()` with key `{user_id}:trip_edit`.
- Thin HTTP proof tests (auth + rate limit + owner happy path); service semantics already covered in 7.2.

**Non-Goals:**

- Full edit/replan pytest matrix (7.4)
- Evaluation polish (7.5) / smoke (7.6)
- Changing TripService edit algorithms
- Adding per-UUID paths to `_route_limit_table`
- New Redis client imports in router

## Decisions

1. **Thin router delegates entirely to TripService**
   - **Choice:** Each handler: resolve `payload` via `Depends(rate_limit_trip_edit)` (which itself Depends `require_auth`), call the matching service method with `payload.user_id`, return `ApiResponse(data=TripOut.from_trip(trip))`.
   - **Why:** AGENT.md Router→Service; ownership/validation already raise WandrError subclasses handled globally.
   - **Alternatives:** Re-check ownership in router — rejected (duplication).

2. **`rate_limit_trip_edit` as FastAPI dependency, not path-table row**
   - **Choice:** Dependency after auth; `key = f"{payload.user_id}:trip_edit"`; limits from settings; on deny raise `RateLimitedError`; on limiter exception return payload (fail open). Document that middleware IP default still applies (dual limit OK).
   - **Why:** Lock #14; UUID path segments cannot exact-match a static `_route_limit_table` entry without hacks.
   - **Alternatives:** Regex path matching in middleware — rejected for this step (step forbids path-table UUID hacks).

3. **`RateLimitedError` in `src/core/exceptions.py`**
   - **Choice:** Small `WandrError` subclass (`status_code=429`, `code="rate_limit_exceeded"`). Middleware may keep inline JSONResponse; dependency raises the class so the global handler maps it.
   - **Why:** Step allows subclass OR bare WandrError; subclass keeps handler mapping consistent with other domain errors and is reusable.
   - **Alternatives:** Raise generic `WandrError(...)` — acceptable but less discoverable.

4. **Dependency module location: `src/trips/dependencies.py`**
   - **Choice:** New small module exporting `rate_limit_trip_edit`; router imports it. Uses `get_rate_limiter` from middleware module (already the Protocol factory).
   - **Why:** Trip-edit-specific; keeps `auth/dependencies.py` stub untouched; avoids bloating router.
   - **Alternatives:** Put on `core/security/permissions.py` — possible but mixes auth with trip product limits.

5. **Default RoutingProvider on service**
   - **Choice:** Router does not pass `routing=`; TripService uses its default `OsrmRoutingProvider` (already from 7.2). Tests mock limiter / inject Fake at service layer in 7.4.
   - **Why:** Matches 7.2 DI design; router stays free of travel_engine / geo imports.
   - **Alternatives:** FastAPI `Depends` for RoutingProvider — unnecessary for MVP.

6. **Thin HTTP tests in this step; full matrix deferred**
   - **Choice:** Minimal tests proving OpenAPI has four routes, owner reorder → 200, guest → 401, other user → 403, mock limiter 21st → 429. Prefer override/mock of `get_rate_limiter` / dependency rather than hammering real windows in CI.
   - **Why:** Step 7.3 ✅ validation lines; step 7.4 owns the broad Fake/HTTP suite.
   - **Alternatives:** Ship full `test_edit_replan.py` now — out of scope / cadence lock.

7. **Existing CRUD routes unchanged**
   - **Choice:** Only append edit routes; DELETE asymmetry / GeoJSON envelope exception remain as P6.
   - **Why:** Step DO NOT list includes optional_auth on edits only — not rewriting P6.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Dual IP + user limits confuse operators | Comment in dependency + context: middleware default still applies |
| Fail-open lets edit spam when Redis down | Same resilience contract as middleware; document known limitation |
| Thin HTTP tests miss service regressions | 7.2 Fake suite already covers ops; 7.4 expands HTTP |
| `RateLimitedError` body lacks `Retry-After` vs middleware | Prefer include `Retry-After` header in handler or raise with details + optional custom response; at minimum ErrorResponse code/message match middleware. Prefer dependency raises WandrError and, if easy, set header via a small response path — document if header only on middleware 429s for MVP |
| Accidental travel_engine import in router | Import guard / review; router only schemas + service + deps |

## Migration Plan

- Config defaults only — no Alembic.
- Deploy: rolling restart; new routes appear in OpenAPI.
- Rollback: revert router/deps/config; clients lose edit HTTP only (service methods remain unused).

## Open Questions

- None blocking. Optional polish: whether `wandr_error_handler` should add `Retry-After` for `RateLimitedError` — prefer yes if one-liner using `exc.details` or settings window; otherwise acceptable MVP gap called out in tasks.
