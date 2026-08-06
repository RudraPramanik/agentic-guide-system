## 1. Update map stack in FE_guide

- [x] 1.1 Replace the §2 Maps one-liner with a short pointer + explicit map-layer table (Renderer MapLibre GL JS; Tile Provider MapTiler free tier; Fallback OSM public tiles development only; Data Format GeoJSON from FastAPI; Future self-hosted/other provider)
- [x] 1.2 Update §4 FE env notes: recommend MapTiler style URL and/or key (`NEXT_PUBLIC_*`); mark OSM public tiles as local/dev-only fallback; no backend tile secrets
- [x] 1.3 Confirm Google Maps remains deferred as primary SDK; §15 GeoJSON contract unchanged (cross-link only if helpful)

## 2. Verify

- [x] 2.1 Spot-check guide: production default is MapTiler, not OSM public tiles
- [x] 2.2 Confirm docs-only scope (no FastAPI / FE scaffold changes)
