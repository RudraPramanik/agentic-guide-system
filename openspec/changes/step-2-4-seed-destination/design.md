## Context

P2.3 + P2.6a/2.6b are done: `PlaceRepository`, `DestinationRepository.upsert_from_geocoded`, `geocode`, `fetch_pois`. `scripts/seed_destination.py` is still a step-0.1 stub. Canonical next: step **2.4** (`docs/steps/step2.md`). Seed is a CLI orchestrator (not a FastAPI router) — allowed to call geo gateways + repositories and commit.

## Goals / Non-Goals

**Goals:**
- CLI: `python scripts/seed_destination.py --destination "Darjeeling" --radius 30`
- Flow: geocode → atomic destination upsert → Overpass → per-POI place upsert (continue on error) → `place_count` via `BaseRepository.update` → commit
- Idempotent re-run (same dest id, no duplicate osm_ids)
- Locked failure boundaries (geocode None / Overpass [] / single POI fail)
- Update `docs/context.md` → Next **2.5**

**Non-Goals:**
- OSRM, destinations/places HTTP, readiness math, pytest modules
- New packages or migrations
- Calling httpx / building OverpassQL in the script

## Decisions

### D1 — Script orchestrates; geo stays in `src/geo/`
- Use `geocode` + `fetch_pois` only. No direct Nominatim/Overpass HTTP in the script.

### D2 — Atomic destination upsert from 2.6b
- Always `DestinationRepository.upsert_from_geocoded` — never inline check-then-insert.

### D3 — Per-POI try/except continue
- On `upsert_from_poi` exception: `get_logger().warning("seed.poi_failed", osm_id=..., error=...)` and continue. Final `success_count` excludes failures. Do not exit 1 for partial POI failures.

### D4 — `place_count` via `BaseRepository.update`
- After the loop: `await dest_repo.update(dest.id, {"place_count": success_count})` — do not touch `enriched_count` / `indexed_count`. Then `session.commit()`.

### D5 — Overpass empty list is success path
- If `fetch_pois` returns `[]`: still upsert destination, set `place_count=0`, commit, print/log warning. Exit 0.

### D6 — Geocode miss is hard fail
- If `geocode` returns `None`: print human-readable error, exit 1, do not open a successful commit path (no destination row required).

### D7 — argparse + asyncio + PYTHONPATH
- Match other scripts: `argparse` for `--destination` (required) and `--radius` (default 30). Call `configure_logging()` at start. Document `PYTHONPATH=project root` for Windows/dev runs.

### D8 — Failure-path-2 validation is loop-pattern proof
- Step’s mocked `python -c` tests the continue-on-error loop pattern (not full CLI). Keep that as a separate validation task; live Darjeeling seed is the integration proof.

## Risks / Trade-offs

- [Public Overpass 504 / slow] → gateway returns `[]` after retries; seed still commits dest with 0 places
- [Nominatim rate limit / miss] → exit 1; operator retries later
- [n < 50 on flaky Overpass] → validation expects `n >= 50` for Darjeeling; override `OVERPASS_API_URL` or retry if public mirror fails
- [Long seed (~150 POIs)] → progress every 10 POIs; single transaction until final commit (acceptable for P2 volumes)

## Migration Plan

1. Implement `scripts/seed_destination.py`
2. Run happy-path + re-run + nonsense geocode + mocked POI-continue validations
3. Update `docs/context.md`
4. No Alembic

## Open Questions

- None blocking.
