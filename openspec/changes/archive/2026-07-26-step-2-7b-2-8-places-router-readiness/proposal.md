## Why

P2.7a shipped `PlaceService` / `PlaceOut`, but places are still unreachable over HTTP — clients cannot list or fetch places. Destinations readiness is mounted but returns an interim stub (`score=0`, `tier=sparse`). Steps **2.7b** and **2.8** are next in the canonical order (`docs/steps/step2.md`): expose places routes, then replace the readiness stub with pure `compute_readiness` so the public catalog surface is complete before P2 pytest/smoke (2.9–2.10).

## What Changes

- Implement `src/places/router.py` — `GET /api/v1/places` (paginated by `destination_id`) and `GET /api/v1/places/{place_id}` via `PlaceService` only
- Register places router in `src/main.py`
- Implement pure `src/destinations/readiness.py` — `compute_readiness` / `ReadinessResult` per locked P2 formula (`PLACE_TARGET=100`, weighted score, tier thresholds)
- Replace interim `DestinationService.get_readiness` stub with real scoring (`search_available=False` in P2; no Qdrant)
- Validate per step2.md curls + readiness unit assert; update `docs/context.md` (2.7b + 2.8 ✅, Next → **2.9**)

**Step readiness:** Both are implementable now — `PlaceService` and destinations readiness route already exist; Darjeeling seed from 2.4 is the HTTP validation fixture. No new packages.

## Capabilities

### New Capabilities

- `places-http`: Places APIRouter (`/api/v1/places`) — list by destination + get by id; registered in `main.py`
- `destination-readiness`: Pure readiness math (`compute_readiness`) + service wiring that returns real `DestinationReadinessOut`

### Modified Capabilities

- `destinations-http`: Readiness endpoint behavior changes from interim stub to formula-backed scores/tiers (404 for unknown id unchanged)

## Impact

- **Code:** `src/places/router.py` (new), `src/main.py`, `src/destinations/readiness.py` (new), `src/destinations/service.py`, `docs/context.md`
- **Live endpoints:** `GET /api/v1/places?destination_id=…`, `GET /api/v1/places/{id}`; readiness returns `tier=limited` / score ≈ 0.4 for seeded Darjeeling (unenriched)
- **Deps:** none new
- **AGENT.md:** Router → Service only; readiness.py has zero SQLAlchemy/FastAPI/httpx/qdrant imports; envelopes remain `ApiResponse` / `PaginatedResponse`
- **Non-goals:** 2.9 pytest modules; 2.10 smoke script; developer-manual refresh; Qdrant / enrichment (P3); Redis (P6)
