## Why

Oracle VPS production returns `404 Destination not found` for cities like London/Paris because public Nominatim returns **403 Access denied** (placeholder `NOMINATIM_USER_AGENT` and/or datacenter IP policy). The API maps every geocode `None` to not-found, so operators and the FE cannot tell “unknown place” from “geo upstream blocked.” Places/prepare/planner then look empty even though auth, Redis, Qdrant, and OSRM are healthy. Fix the failure semantics and give prod a supported path off public OSM Nominatim.

## What Changes

- **BREAKING (API semantics):** `GET /api/v1/destinations/search` MUST return **502** `external_service_error` (service=`nominatim`) when the geocode upstream rejects the request (4xx policy/rate-limit such as 403/429), instead of **404** `not_found`. True empty Nominatim results and geocode timeouts remain **404** `not_found`.
- Geocoder MUST NOT store process-cache `None` for upstream 4xx client errors (so a fixed User-Agent or provider swap works without waiting for process restart for those queries). Empty successful responses may still be cached as `None`.
- Optional `NOMINATIM_API_KEY` (via `get_settings()`) for Nominatim-compatible commercial endpoints; when set, attach as query `key` (LocationIQ-style). `NOMINATIM_BASE_URL` remains the switch to leave `nominatim.openstreetmap.org`.
- Production env examples + VPS ops docs MUST require a real contact User-Agent (no `contact@example.com`), document public-OSM risk from cloud IPs, and recommend provider swap + Overpass mirror / `PLACES_SOURCES` order when Overpass returns 4xx.
- Overpass gateway: send an explicit `Accept: application/json` alongside existing User-Agent (mitigate 406-class mirror rejections where possible). No new packages.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `geo-geocoder`: Upstream 4xx must surface as a typed failure (not silent `None`); no negative-cache of those failures; optional API key for compatible Nominatim URLs.
- `destinations-core`: Cache-aside search raises `ExternalServiceError` when geocode signals upstream failure; `None` still means not found.
- `destinations-http`: Search HTTP contract: 502 on geocode upstream failure vs 404 for un-geocodable / timeout.
- `geo-overpass`: HTTP headers include `Accept: application/json` with existing User-Agent.
- `production-deployment-blueprint`: Prod geo env checklist — real UA, Nominatim provider guidance, Overpass/`PLACES_SOURCES` fallback notes.

## Impact

- **Code:** `src/geo/geocoder.py`, `src/geo/overpass.py`, `src/destinations/service.py`, `src/config.py`; tests under `tests/geo/`, `tests/destinations/` (or equivalent).
- **API:** Search error envelope for upstream blocks changes from 404 → 502 (**BREAKING** for clients that treated all search failures as not-found).
- **Config / ops:** `.env.example`, `.env.production.example`, `docs/vps.md` (and related production checklist). No Compose/Dockerfile changes.
- **AGENT.md:** Geo I/O stays in `src/geo/`; settings only via `get_settings()`; `ExternalServiceError` already exists in `src/core/exceptions.py`.
- **Non-goals:** Self-hosted Nominatim/Photon stack; FE changes; planner/graph changes; Redis geocode cache; changing default public URLs for local dev; implementing a full multi-provider geocode abstraction beyond URL + optional key.

## AGENT.md constraints that apply

- Geo only via `src/geo/`
- Env only via `get_settings()`
- ApiResponse / ErrorResponse envelopes; no raw exception leaks
- No new packages without requirements.txt + why-comment (none expected)
