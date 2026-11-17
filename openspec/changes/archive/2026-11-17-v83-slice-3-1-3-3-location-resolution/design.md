## Context

See proposal.md — Why. `geocode_search` in `src/geo/geocoder.py` already returns a list of `GeocodedPlace` with timeout, tenacity, and an empty list on network failure. `DestinationRepository.search_by_name` is a read. `DestinationService.search` and `resolve` upsert and own the public HTTP shapes. This change adds a library beside them. It does not call them, and they do not call it.

## Goals / Non-Goals

**Goals:**

- One package, `src/location_intelligence/`, whose pure functions are deterministic for a fixture and whose only I/O is the existing geocoder plus a read-only catalog port.
- Settings from §7.2 present and defaulted, unread by generate.
- Search areas that a later retrieval filter can consume without guessing a 30 km radius.

**Non-Goals:**

- See proposal.md — Non-goals. In particular, `test_area_respect` stays skipped, and oversized admin does not call the existing hub picker.

## Decisions

### 1. Pure core, thin async facade

`schemas.py` holds `LocationType`, `ResolvedLocation`, `LocationResolution`, `SearchArea`, and a plain `CatalogHit` (name, country, display name, osm id, lat, lng, catalog id). No SQLAlchemy model in the schemas.

`confidence.py`, `resolver.py`, and `search_area.py` are pure. They take hits, catalog rows, and a radius policy. They do not import `httpx`, the geocoder, or a repository.

`service.py` is the only module that calls `geocode_search` and the catalog port. Tests of classification, resolution, and area pass fixtures straight into the pure functions. The service test injects both ports.

Alternative: fold this into `DestinationService.resolve`. Rejected. That method upserts and returns `DestinationResolveOut`. Changing it would change `GET /api/v1/destinations/resolve`.

### 2. Catalog port is read-only

The default port calls `DestinationRepository.search_by_name` and maps rows to `CatalogHit`. It does not commit and does not call `upsert_from_geocoded`. Unit tests pass an in-memory list, so the suite does not need Postgres. A merge writes nothing even when the default port is used.

Alternative: candidate search upserts a miss, matching `DestinationService.search`. Rejected. A library call would then create destinations as a side effect before any planner flag is on.

### 3. Confidence from type priors, not a new Nominatim field

`GeocodedPlace` has no `importance`. Editing `geocoder.py` to store it is outside this change and would revise `geo-geocoder`. Priors and the catalog bump are specified in `specs/location-intelligence/spec.md`. The distance test for the 1 km catalog bump is a pure haversine in this package. No new dependency.

Alternative: parse `importance` in the geocoder. Deferred. A later slice can add the optional field and replace the prior; until then the numbers in the spec are the contract.

### 4. Search-area policy object, filled from settings at the edge

`build_search_area` takes the anchor, an optional user radius, an optional GeoJSON dict, and a policy object with the four radius numbers and the confidence threshold's sibling defaults. `service.py` builds that policy from `get_settings()`. Pure tests construct the policy with the spec defaults and do not read the environment.

City bbox becomes a closed GeoJSON polygon ring `[west, south] → [east, south] → [east, north] → [west, north] → close`. Bounding boxes on candidates are `[west, south, east, north]`.

Address reuses `LOCATION_NEIGHBORHOOD_RADIUS_KM`. §7.2 has no address knob, and this change does not invent one.

Country and region raise a typed error (`oversized_admin`). They do not return a `SearchArea`. Invalid polygons raise a typed error (`invalid_polygon`). No shapely and no self-intersection check.

Alternative: a 15 km fallback for countries. Rejected. That recreates the hidden-radius problem §6.3 is written to stop. Row 3.4 can map the typed error onto the existing hub response.

### 5. Resilience stays on the geocoder

`geocode_search` already uses `httpx.Timeout(connect=5, read=10, write=10, pool=5)`, tenacity (3 attempts, 1–8 s, timeout and connect errors only), and a named fallback of `[]` on other HTTP failures. 403/429 raise `ExternalServiceError` and are not cached as misses.

`service.py` wraps that call in `asyncio.wait_for(..., timeout=SEARCH_GEOCODE_TIMEOUT_SECONDS)`. Timeout → `LocationResolution` `not_found` / `geocoder_timeout`. `ExternalServiceError` propagates. The catalog read has no HTTP. This package adds no retry of its own.

### 6. The flag is stored and unread

`LOCATION_V2_ENABLED` defaults to false next to `RUN_TRACKING_ENABLED` in `src/config.py`, with the same comment style: off until row 3.4 branches generate. A test scans `src/planner/**` and `src/travel_engine/**` and fails if the flag name or `src.location_intelligence` appears. The architecture suite already asserts the default once the field exists (`tests/architecture/_helpers.py`). This change does not edit that suite.

### 7. Completion sync is two doc rows

After `pytest tests/location_intelligence -v` is green, update `docs/context.md` (next blueprint row is 3.4; generate is unchanged) and the matching rows in `docs/v8.2/repository_audit.md` (package implemented-tested; settings present and unread by the planner). Do not mark the Slice 3 exit gate done. That gate needs the location golden suite, which is row 3.4.

## Risks / Trade-offs

- [Type prior disagrees with a later provider score] → The spec numbers stay until a reviewed spec change. Do not silently switch to Nominatim `importance`.
- [Loose catalog `ILIKE` rows look like a second city] → Only an exact normalized name inside 1 km, or the same OSM id, can merge or bump confidence. Substring hits stay separate candidates and keep their own prior.
- [A future import wires the library into generate inside this slice] → The scan test forbids `src.planner` and `src.travel_engine` imports. Review rejects a router.
- [Operators set `LOCATION_V2_ENABLED=true` and expect a new search area] → The flag does nothing until 3.4. `docs/context.md` and the config comment say so. Rollback is still "flag off", which is a no-op here.
- [Rectangle bbox is not the real city polygon] → `fallback_used` stays false only when Nominatim supplied a bbox. The description names it as a bbox rectangle. A true admin polygon waits until a provider returns one; this change does not add that call.

## Migration Plan

No migration and no backfill. Deploy is the new package plus settings defaults. Existing destination search, resolve, and generate paths are untouched.

Rollback: set `LOCATION_V2_ENABLED=false` (already the default; nothing reads it) and delete `src/location_intelligence/` plus the new settings if the package must leave the tree. No downgrade SQL.
