## ADDED Requirements

### Requirement: Explicit FE map layer recommendations in FE_guide

`docs/FE_guide.md` MUST document the Wandr MVP map stack as distinct layers: MapLibre GL JS as renderer, MapTiler free tier as the recommended tile provider, OpenStreetMap public tiles as a development-only fallback, trip overlay data as GeoJSON from FastAPI, and a future option for self-hosted tiles or another provider. The guide MUST NOT present OSM public tiles as the production basemap default.

#### Scenario: Map stack table present

- **WHEN** a frontend developer reads the maps guidance in `docs/FE_guide.md`
- **THEN** the guide MUST list Renderer, Tile Provider, Fallback, Data Format, and Future with the recommendations above
- **AND** MUST keep MapLibre as the primary map SDK (Google Maps MUST remain deferred/rejected as primary)

#### Scenario: Overlay data source

- **WHEN** documenting map data format
- **THEN** the guide MUST state that itinerary geometry comes from FastAPI GeoJSON (trip geojson endpoint already contracted in the guide)
- **AND** MUST NOT require a separate tile/vector backend in this API repo for MVP overlays

### Requirement: FE env for MapTiler vs OSM fallback

`docs/FE_guide.md` MUST update frontend environment guidance so MapTiler configuration (style URL and/or API key as public FE env) is the recommended path for real map basemaps, and OpenStreetMap public tiles are marked development-only. Backend env MUST NOT gain MapTiler secrets as part of this change.

#### Scenario: Local vs recommended tiles

- **WHEN** configuring the sibling Next.js app for maps
- **THEN** the guide MUST allow a local/dev fallback to OSM public tiles
- **AND** MUST recommend MapTiler free tier for non-dev use
- **AND** MUST keep tile credentials out of backend `.env` / server secrets

### Requirement: Docs-only scope

Applying this change MUST update documentation in the API repo (`docs/FE_guide.md`) without requiring FastAPI route changes or scaffolding the Next.js application.

#### Scenario: No backend or FE scaffold work

- **WHEN** this change is applied
- **THEN** only guide (and optional one-line cross-ref) docs MUST change
- **AND** live trip GeoJSON behavior MUST remain unchanged
