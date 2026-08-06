## Why

P7 day-edit ops need a stable generation origin for `travel_matrix` / polylines. `TravelState` already carries `base_lat`/`base_lng`, but `TripService.save_from_state` does not persist them on `Trip.preferences`, so later edits would invent an origin. Step **7.0** in `docs/steps/step7.md` (v2.1) is the locked first code batch — implement it cleanly before any edit HTTP or shared-geometry work.

## What Changes

- Extend `TripService.save_from_state` to copy numeric `base_lat` / `base_lng` from state into `Trip.preferences` when present; omit keys when absent (legacy-safe).
- Add `_resolve_base(trip, destination) -> tuple[float, float]` preferring numeric prefs, else `Destination.lat`/`lng`; never raises 500.
- Add/extend pytest coverage in `tests/trips/` for save prefs + resolve prefs-win / destination-fallback / non-numeric fallback.
- Bump `docs/context.md` Progress for **7.0** only after tests green; set Next step to **7.1**.
- **Non-goals:** edit endpoints, `populate_leg_polylines`, preserve-order schedule, `TripEditEvent` on edit, migrations/new columns, PlannerService/LLM, GeoJSON/SSE changes, 7.1–7.6 code.

## Capabilities

### New Capabilities
- *(none — 7.0 extends existing trips persistence)*

### Modified Capabilities
- `trips-repository-service`: `save_from_state` persists base coords in preferences; `_resolve_base` helper for P7 edit preamble (used by later steps; shipped and tested in 7.0).

## Impact

- **Code:** `src/trips/service.py`; `tests/trips/test_save_from_state.py` (or focused new test module).
- **Docs:** `docs/context.md` Progress/Next step after green; implement from `docs/steps/step7.md` §7.0 only.
- **AGENT.md:** Router→Service→Repository unchanged; no geo/LLM; no new packages; env via settings N/A for this delta.
- **Downstream:** Unblocks honest 7.2 edit routing; trips saved before 7.0 still fall back to destination centroid (documented MVP limitation).
