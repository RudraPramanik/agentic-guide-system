## Why

`docs/FE_guide.md` currently collapses maps into one stack cell (“MapLibre GL + OSM-compatible tiles”) and lists MapTiler as an optional later env. The FE team needs an explicit renderer vs tile-provider split so production defaults to MapTiler (free tier), OSM public tiles stay development-only, trip overlays stay GeoJSON from FastAPI, and a future self-hosted/other-provider path is documented — without changing the MapLibre + no-Google-Maps MVP lock.

## What Changes

- Update `docs/FE_guide.md` locked stack / maps guidance to an explicit map-layer table:
  - Renderer: MapLibre GL JS
  - Tile provider: MapTiler (free tier)
  - Fallback: OpenStreetMap public tiles (development only)
  - Data format: GeoJSON from FastAPI (`GET /trips/{id}/geojson`)
  - Future: self-hosted tiles or another provider
- Align the FE env notes so a MapTiler key/URL is the recommended production path (still frontend-only; never backend secrets).
- Keep Google Maps deferred/rejected as primary SDK; do not change backend GeoJSON contract.

## Capabilities

### New Capabilities

- `fe-guide-map-tiles`: Requirements for documenting Wandr’s FE map stack as MapLibre renderer + MapTiler tiles (OSM public tiles as dev-only fallback) + FastAPI GeoJSON overlay data, with a documented future tile-hosting option.

### Modified Capabilities

- (none — `frontend-stack-guide` is not yet in `openspec/specs/`; this change adds a focused map-tiles capability rather than a delta against a missing main spec)

## Impact

- **Docs:** `docs/FE_guide.md` (stack table, env vars for tiles, possibly a short map subsection).
- **OpenSpec:** `openspec/changes/fe-guide-map-tiles/`.
- **Code:** none — documentation only; no FastAPI or FE scaffold.
- **Non-goals:** implementing MapLibre in a FE repo; changing GeoJSON schema; self-hosting tiles now; adopting Google Maps.
