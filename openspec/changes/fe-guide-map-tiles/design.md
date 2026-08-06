## Context

`docs/FE_guide.md` locks MapLibre for trip maps but phrases tiles as “OSM-compatible” and treats MapTiler as optional/later in the env table. Product direction is clearer: MapLibre GL JS as renderer, MapTiler free tier as the recommended tile provider, OSM public tiles only as a development fallback, overlay data from FastAPI GeoJSON, with room to swap tile hosts later. This is a docs-only clarification for the sibling Next.js team.

## Goals / Non-Goals

**Goals:**

- Replace the single Maps stack row (and related env wording) with an explicit map-layer recommendation table.
- Keep trip geometry sourced from `GET /trips/{id}/geojson` (already documented in §15).
- Document FE-only env for MapTiler (e.g. style URL / API key) without putting secrets on the backend.

**Non-Goals:**

- Scaffolding or implementing map components in a FE repo.
- Changing FastAPI GeoJSON shape or trip routers.
- Self-hosting tiles or signing up for MapTiler in this change.
- Adopting Google Maps JS as primary SDK.

## Decisions

### D1 — Split renderer vs tiles vs data

Document five rows (as requested):

| Layer | Recommendation |
|-------|----------------|
| Renderer | MapLibre GL JS |
| Tile Provider | MapTiler (free tier) |
| Fallback | OpenStreetMap public tiles (development only) |
| Data Format | GeoJSON from FastAPI |
| Future | Self-hosted tiles or another provider |

- **Why:** Avoids implying OSM public tiles are the production basemap; separates basemap hosting from itinerary data.
- **Alternatives:** Keep one-line “OSM-compatible” — rejected as ambiguous for FE setup.

### D2 — Where to place the table in `FE_guide.md`

- **Choice:** Keep a concise Maps cell in §2 pointing to a short **Map stack** subsection (or expand §2 with a nested table under Maps). Update §4 env: MapTiler key/style URL as recommended (not “later”); note OSM public tiles for local-only fallback.
- **Why:** Stack table stays scannable; detail lives next to maps guidance.
- **Do not** duplicate the full GeoJSON property catalog (already §15).

### D3 — Env naming (FE only)

- **Choice:** Document something like `NEXT_PUBLIC_MAP_STYLE_URL` and/or `NEXT_PUBLIC_MAPTILER_KEY` (exact names chosen at apply time to match common MapLibre+MapTiler patterns; keep to 1–2 vars). Mark OSM raster/style URL as optional local override only.
- **Why:** FE needs a concrete env story; backend remains free of tile keys.

### D4 — Google Maps stays deferred

- No change to deferred table intent; MapLibre remains primary.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| MapTiler free-tier limits in prod | Document free tier + Future row for self-host/other provider |
| OSM public tile ToS / rate limits if used in prod | Explicit “development only” on fallback |
| Env var name bikeshedding | Prefer one style URL if possible; key only if MapTiler style URL needs it |

## Migration Plan

1. Edit `docs/FE_guide.md` only.
2. No runtime deploy.
3. Rollback: revert doc commit.

## Open Questions

- Exact public env var names (`NEXT_PUBLIC_MAP_STYLE_URL` vs key + default style) — resolve at apply with a single preferred pattern.
