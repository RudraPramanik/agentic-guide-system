## Context

See `proposal.md` for motivation. Today `ingest_destination_pois` / prepare / seed call `fetch_pois` only. OverpassQL is locked to six tourism tags. `Place.osm_id` is unique (`node/…` / `way/…`). Geo I/O must stay in `src/geo/`. No new HTTP endpoints.

## Goals / Non-Goals

**Goals:**

- Widen Overpass retrieval into existing `RawPOI` → upsert path.
- Add a settings-driven places facade so optional OpenTripMap (and later Geoapify) can contribute without callers knowing sources.
- Keep prepare/seed HTTP/CLI contracts, fail-soft empty lists, and `osm_id` uniqueness.
- Document which env keys are required when optional sources are enabled.

**Non-Goals:**

- Live ranking rewrite or Qdrant schema changes.
- Offline Overture/FSQ dumps.
- Renaming `places.osm_id` or Alembic migration for this change.
- Replacing Nominatim or changing `ROUTING_BACKEND`.

## Decisions

### D1 — Facade over replace

**Choice:** `fetch_destination_pois(lat, lng, radius_km) -> list[RawPOI]` in `src/geo/` orchestrates configured sources. Overpass remains the default and sole source when `PLACES_SOURCES=overpass`.

**Why:** Prepare/seed already depend on `RawPOI`. Swapping Overpass for a single commercial API would couple product quality to one vendor and break offline/fail-soft habits.

**Alternatives:** Hard-swap to Geoapify only (rejected — keys + attribution + loses free OSM path); call multiple APIs from ingest (rejected — violates geo gateway rule).

### D2 — Keep `osm_id` column; prefix foreign ids

**Choice:** Treat `Place.osm_id` as opaque external id. OSM stays `{type}/{id}`. OpenTripMap → `otm:{xid}`. Geoapify → `geoapify:{place_id}`. No migration.

**Why:** Avoids Alembic risk and keeps `upsert_from_poi` / unique constraint working.

**Alternatives:** Rename column to `external_id` (deferred); separate `source` column (nice later, not required for prototype).

### D3 — Widen Overpass tags + map new categories

**Choice:** Extend OverpassQL to include (at minimum):

- `amenity=cafe|restaurant`
- `amenity=place_of_worship` (and/or `tourism=monastery` kept)
- `historic=*` (named only)
- `natural=peak|waterfall` (and keep park/trailhead/tourism set)

Map to structural categories: `cafe`, `restaurant`, `temple`, `historic`, `nature`, plus existing P2 set. Unknown → `attraction`.

**Why:** Free, no API key, largest immediate mix fix for hill-station / city prototypes.

**Alternatives:** Only add commercial Places API (rejected as first step — still leaves OSM thin).

### D4 — OpenTripMap as first optional secondary

**Choice:** Implement OpenTripMap client behind the facade when `opentripmap` ∈ `PLACES_SOURCES`. Requires `OPENTRIPMAP_API_KEY`. Store rate/kinds in `raw_tags` for future ranking. Default sources remain `overpass` only so CI/dev boots without a new key.

**Why:** Tourism-focused, popularity `rate`, ODbL-friendly caching into PostGIS, free 5k/day (non-commercial — acceptable for prototype). Prefer over Geoapify as the first optional source.

**Alternatives:** Geoapify-first (keep as optional third source, default off); Foursquare live API (quota too small).

### D5 — Dedupe before upsert

**Choice:** After union of sources, dedupe by exact `osm_id`, then by normalized name + haversine distance ≤ ~75 m (same category preferred). Prefer OSM id when colliding with a synthetic id (keep OSM row; drop duplicate foreign). Cap is soft — no hard max in this change.

**Why:** Prevents double cafes from OSM + OpenTripMap inflating `place_count` without improving itineraries.

### D6 — Settings surface

```
PLACES_SOURCES=overpass          # comma list: overpass,opentripmap,geoapify
OPENTRIPMAP_API_KEY=             # required if opentripmap enabled; empty → skip source + log warning
OPENTRIPMAP_BASE_URL=https://api.opentripmap.io/0.1/en
GEOAPIFY_API_KEY=                # required if geoapify enabled; empty → skip
GEOAPIFY_BASE_URL=https://api.geoapify.com/v2
```

Missing key for an enabled optional source MUST NOT fail prepare/seed: skip that source, log warning, continue with remaining sources (same fail-soft spirit as Overpass `[]`).

### D7 — travel_rules durations for new categories

**Choice:** Add explicit minutes: `cafe=30`, `restaurant=60`, `temple=40`, `historic=40`, `nature=45`. Default 30 remains for unknowns.

**Why:** Schedule realism; avoids treating a restaurant like a viewpoint (20 min).

### D8 — Resilience

- Overpass: keep existing tenacity + `[]` on failure.
- OpenTripMap / Geoapify: connect/read timeouts via httpx; retry transient 5xx; on exhausted failure return `[]` for that source only (do not abort the union).
- No new third-party Python packages unless httpx already insufficient (prefer std + httpx).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Wider Overpass = slower / 504s on public mirrors | Keep `read=90`, retries; operators may set private `OVERPASS_API_URL` |
| OpenTripMap free = non-commercial | Document in `.env.example`; switch to Geoapify or owned dump before commercial launch |
| `place_count` jumps after re-prepare; enrich/index lag | Prepare still skips enrich/index (unchanged); operators re-run enrich/index scripts |
| Dedupe false merges | Conservative 75 m + name normalize; prefer keeping more uniques over aggressive merge |
| Category inflation breaks morning/avoid rules | New cats not in `MORNING_ONLY` / `AVOID_SAME_DAY` unless explicitly added later |

## Migration Plan

1. Ship code with `PLACES_SOURCES=overpass` (behavior = wider OSM only; no new keys).
2. Re-prepare or re-seed target destinations; optionally re-enrich / re-index.
3. Optionally set OpenTripMap key and `PLACES_SOURCES=overpass,opentripmap`.
4. Rollback: set `PLACES_SOURCES=overpass` and/or revert Overpass template via git; existing extra rows remain (soft-delete / leave in place — no destructive wipe required).

**Open questions (resolved during apply):** Geoapify `place_id` strings exceed `places.osm_id` VARCHAR(64). Client now stores `geoapify:{sha1(place_id)}` and keeps the original id in `raw_tags.geoapify_place_id` — no Alembic migration.
