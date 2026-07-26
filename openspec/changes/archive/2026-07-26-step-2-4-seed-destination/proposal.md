## Why

P2.6a/2.6b delivered destination schemas + atomic `upsert_from_geocoded` and cache-aside search, and P2.3 delivered `PlaceRepository.upsert_from_poi` — but there is still no CLI to load a destination’s Overpass POIs into Postgres. Step **2.4** (`docs/steps/step2.md`) is next per `docs/context.md`: seed unlocks places APIs, readiness, and later P2 validation.

## What Changes

- Replace stub `scripts/seed_destination.py` with real CLI: `--destination` / `--radius` → geocode → destination upsert → Overpass → per-POI place upsert → set `place_count` → commit
- Failure boundaries locked: geocode miss → exit 1 (no commit); Overpass `[]` → save destination with `place_count=0` + warning; single POI error → log + continue
- Validate Darjeeling seed + idempotent re-run + nonsense geocode + mocked single-POI survival; update `docs/context.md` (2.4 ✅, Next → **2.5**)

**Step readiness:** §2.4 is good to go as written — depends on already-built 2.6b + 2.3; no step-doc amendment required.

## Capabilities

### New Capabilities

- `seed-destination`: CLI seed pipeline (geo gateways + destination/place repositories; commits on success)

### Modified Capabilities

- *(none)*

## Impact

- **Code:** `scripts/seed_destination.py` only (orchestrates existing modules)
- **Deps:** none new — `geocode`, `fetch_pois`, `DestinationRepository`, `PlaceRepository`, `AsyncSessionLocal`, structlog
- **AGENT.md:** script may call `src/geo/` + repositories; MUST NOT call httpx/Overpass/Nominatim directly; no LLM
- **Non-goals:** OSRM (2.5), destinations router (2.6c), places service/router (2.7), readiness (2.8), pytest suite (2.9)
- **Note:** complete-but-unarchived change `step-2-6a-2-6b-destinations-core` should be archived separately; unrelated to this seed work
