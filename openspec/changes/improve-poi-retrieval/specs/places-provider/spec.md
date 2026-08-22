## Purpose

Settings-driven multi-source POI retrieval under the geo layer: normalize every source into RawPOI lists so prepare and seed keep one upsert path.

## ADDED Requirements

### Requirement: Places retrieval facade is the only ingest entry point

The system SHALL expose a geo-layer facade that returns `list[RawPOI]` for a destination point and radius. Destination prepare and seed pipelines MUST obtain POIs only through this facade (not by calling Overpass or third-party Places APIs directly). The facade MUST live under `src/geo/` and MUST NOT import SQLAlchemy, FastAPI, or database sessions. All env for sources MUST come from `get_settings()`.

#### Scenario: Prepare uses the facade

- **WHEN** destination prepare seeds places for a stored lat/lng and radius
- **THEN** POIs are fetched via the geo places facade and no OverpassQL or OpenTripMap/Geoapify HTTP is constructed outside `src/geo/`

#### Scenario: Seed CLI uses the facade

- **WHEN** `scripts/seed_destination.py` runs after a successful geocode
- **THEN** it obtains POIs via the same facade used by prepare

### Requirement: Configurable sources with fail-soft optional keys

`PLACES_SOURCES` MUST be a comma-separated list of source ids. Supported ids include at least `overpass`, `opentripmap`, and `geoapify`. Default MUST be `overpass` only. If an optional source is listed but its API key setting is empty, the facade MUST skip that source, log a warning, and continue with remaining sources. Failure of one source MUST NOT abort others; a fully failed union MUST return `[]` without raising httpx exceptions to callers.

#### Scenario: Default needs no new API keys

- **WHEN** settings leave `PLACES_SOURCES` at the default `overpass`
- **THEN** place retrieval does not require `OPENTRIPMAP_API_KEY` or `GEOAPIFY_API_KEY`

#### Scenario: Missing optional key skips that source

- **WHEN** `PLACES_SOURCES` includes `opentripmap` and `OPENTRIPMAP_API_KEY` is empty
- **THEN** OpenTripMap is skipped with a warning and Overpass (if enabled) still runs

#### Scenario: One source failure does not empty a successful sibling

- **WHEN** Overpass returns POIs and OpenTripMap fails after retries
- **THEN** the facade returns the Overpass POIs (after dedupe) and does not raise to the caller

### Requirement: Stable external ids on RawPOI.osm_id

Every RawPOI MUST carry a stable `osm_id` string suitable for unique upsert. OSM elements MUST keep `{type}/{id}`. OpenTripMap-derived POIs MUST use the prefix `otm:`. Geoapify-derived POIs MUST use the prefix `geoapify:`. The facade MUST NOT require a database migration to introduce non-OSM sources.

#### Scenario: OSM id shape unchanged

- **WHEN** an Overpass node `12345` is mapped
- **THEN** `osm_id` is `node/12345`

#### Scenario: OpenTripMap id is prefixed

- **WHEN** an OpenTripMap place with xid `W123` is mapped
- **THEN** `osm_id` is `otm:W123`

### Requirement: Cross-source deduplication before return

The facade MUST deduplicate the union of source results before returning: exact `osm_id` first; then near-duplicate detection using normalized name and distance within approximately 75 meters. When an OSM-sourced POI and a foreign-sourced POI collide as near-duplicates, the OSM-sourced POI MUST be kept.

#### Scenario: Exact id collision collapses

- **WHEN** two sources emit the same `osm_id`
- **THEN** the returned list contains one entry for that id

#### Scenario: Near-duplicate prefers OSM

- **WHEN** an Overpass cafe and an OpenTripMap cafe share a normalized name within ~75 m
- **THEN** the returned list keeps the Overpass entry and drops the OpenTripMap duplicate

### Requirement: Optional OpenTripMap enrichment of raw_tags

When OpenTripMap is enabled and succeeds, mapped RawPOI `raw_tags` MUST include the provider rate (popularity proxy) and kinds/kinds-equivalent metadata when present in the API response, so later ranking or enrich steps MAY use them without a schema change.

#### Scenario: Rate stored in raw_tags

- **WHEN** OpenTripMap returns a place with a numeric rate
- **THEN** the corresponding RawPOI `raw_tags` includes that rate under a stable key (e.g. `otm_rate`)
