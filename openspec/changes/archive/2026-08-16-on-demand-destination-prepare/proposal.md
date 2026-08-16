## Why

Search already geocodes any place into a destination shell, but that row has `place_count=0` until an operator runs `scripts/seed_destination.py`. Guests then see readiness Score 0 / Places 0 and `POST /planner/generate` returns 409 `destination_not_ready`. Only pre-seeded Darjeeling is plannable. We need a public, place-based prepare path so search → seed POIs → generate works without login and without country/region scrape.

## What Changes

- Add a **public** destination prepare API (no Google/login) that seeds Overpass POIs for an existing destination using the current geocoded point + radius (default 30 km)
- Keep `GET /destinations/search` fast: DB hit or Nominatim shell only — **do not** scrape Overpass inside search
- Reuse the existing seed pipeline (`seed_destination_into` / `_seed_from_geocoded` / `seed_places`); HTTP prepare updates `place_count` the same way the CLI does
- Leave planner floor unchanged: generate still 409 when `place_count < PLANNER_ABSOLUTE_MIN_PLACES` (default 10)
- Rate-limit prepare separately from search (Overpass is expensive)
- Update `docs/FE_guide.md` so the sibling Next.js app knows: search any place → prepare → poll readiness until `place_count` meets the floor → guest generate; do not require login; do not treat empty readiness as a frontend bug
- Idempotent re-prepare: already-seeded destinations MUST NOT wipe counters via geocode upsert

**Not breaking** for existing seeded destinations (Darjeeling path unchanged).

## Capabilities

### New Capabilities

- `destination-prepare`: Public prepare/seed of a geocoded destination (service + HTTP). Place-based radius scrape; guest/unauthenticated; kickoff then poll readiness; empty Overpass stays a non-plannable destination.

### Modified Capabilities

- `destinations-http`: Mount the prepare route on the existing destinations router (`ApiResponse`, router → service only)
- `seed-destination`: Seed pipeline functions MAY be called from `DestinationService` (not CLI-only); `upsert_from_geocoded` still MUST NOT touch `place_count` / enrich / index counters
- `rate-limit-middleware`: Add an IP-keyed prepare limiter (UUID path cannot use the exact-match route table; same pattern as trip-edit)
- `frontend-dev-blueprint`: `docs/FE_guide.md` MUST document prepare, poll-readiness, generate 409 floor, and guest (no-login) generate/trip GET — without inventing auth or country ingest

## Impact

- **Code:** `src/destinations/router.py`, `src/destinations/service.py`, `src/destinations/schemas.py`, `src/destinations/exceptions.py` (as needed), `src/config.py` (prepare rate-limit settings), `src/core/middleware/rate_limit.py`, `scripts/seed_destination.py` (shared helpers only if needed), tests under `tests/destinations/`
- **Docs:** `docs/FE_guide.md` (auth matrix, MVP flow, error codes, DTO if new); `docs/context.md` Live endpoints after apply
- **Deps:** none new — Overpass/Nominatim stay behind `src/geo/`
- **AGENT.md:** Router → Service → Repository; geo only via `src/geo/`; no LLM on prepare; envelopes `ApiResponse`; env via `get_settings()`
- **FE repo:** no code in this change; sibling Next.js follows the updated `FE_guide.md` in a later PR
- **Non-goals:** country/region polygons; Google/login or `require_auth` on generate; making `GET /trips` public; stripping `wandr_session` ownership; LLM enrich or Qdrant index on the prepare path; seeding inside `GET /destinations/search`; lowering `PLANNER_ABSOLUTE_MIN_PLACES`; job queue / new DB columns unless design proves they are required
