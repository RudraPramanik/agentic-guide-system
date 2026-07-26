## Why

P2.5+2.6c shipped OSRM and public destinations search, but every cache-miss on `/destinations/search` still only has P1’s generic 60/min/IP guard — too loose for live Nominatim. Step **2.6c′** closes that. Step **2.7a** is next in the canonical order and unlocks the places service layer (schemas + mandatory destination-existence check) so **2.7b** can expose HTTP without inventing domain logic. Bundling both keeps momentum: rate-limit is a small config/middleware delta; places service is the natural follow-on.

## What Changes

- Add destinations-search rate-limit settings (`20` req / `60` s / exact path) to `config.py` + `.env.example`
- Generalize `_resolve_limits` to an ordered settings-driven route table (planner + destinations search); keep fail-open and existing P1 tests green
- Replace stub `src/places/schemas.py` with `PlaceOut` (lat/lng from geometry via `to_shape`)
- Replace stub `src/places/service.py` with `PlaceService.list_by_destination` / `get_by_id` — destination existence check **mandatory** (`DestinationNotFoundError`) before paginated list
- Validate per step2.md scripts; update `docs/context.md` (2.6c′ + 2.7a ✅, Next → **2.7b**)

**Step readiness:** Both are implementable now — `RateLimitMiddleware` + planner path exist; `PlaceRepository.list_by_destination` and `DestinationRepository.get_by_id_or_raise` exist; Darjeeling seed from 2.4 is the validation fixture.

## Capabilities

### New Capabilities

- `places-service`: `PlaceOut` schema + `PlaceService` (destination-existence check, paginated list, get-by-id)

### Modified Capabilities

- `rate-limit-middleware`: path-specific table lookup; destinations `/search` at 20/min/IP; planner 10/min unchanged; unrelated paths keep default

## Impact

- **Code:** `src/config.py`, `.env.example`, `src/core/middleware/rate_limit.py`, `src/places/schemas.py`, `src/places/service.py`, `docs/context.md`
- **Live behavior:** `GET /api/v1/destinations/search` responses show `X-RateLimit-Limit: 20`; 21st rapid request → 429
- **Deps:** none new — geoalchemy2 already present for `to_shape`
- **AGENT.md:** all limits via `get_settings()`; service uses repositories only (no DB in future router); no hardcoded path strings outside config
- **Non-goals:** 2.7b places HTTP router / `main.py` registration; 2.8 readiness math; 2.9 pytest modules; Redis rate limiter (P6)
