## Purpose

Destination domain core — Pydantic schemas + not-found exception, atomic geocode upsert repository, and cache-aside search service (no HTTP router yet).

## Requirements

### Requirement: Destination schemas and not-found exception

The system SHALL expose Pydantic models `DestinationOut`, `DestinationSearchQuery` (`q` length 2–200), and `DestinationReadinessOut` in `src/destinations/schemas.py` with no imports from models, repository, or geo. The system SHALL expose `DestinationNotFoundError` subclassing `NotFoundError` with `status_code` 404 and optional `query` / `destination_id` details.

#### Scenario: Schema and exception imports

- **WHEN** `DestinationOut`, `DestinationReadinessOut`, and `DestinationNotFoundError` are imported
- **THEN** constructing `DestinationNotFoundError(query="Atlantis")` yields `status_code == 404`

### Requirement: Atomic destination upsert from geocode

The system SHALL persist destinations via `DestinationRepository.upsert_from_geocoded(geocoded)` using a single PostgreSQL `INSERT ... ON CONFLICT (osm_place_id) DO UPDATE ... RETURNING Destination`. The ON CONFLICT SET clause MUST update only geocode-derived fields (`name`, `country`, `display_name`, `lat`, `lng`, `updated_at`) and MUST NOT include `place_count`, `enriched_count`, or `indexed_count`. The repository MUST NOT use check-then-insert and MUST NOT commit (flush/execute only).

#### Scenario: Repeated upsert same osm_place_id

- **WHEN** `upsert_from_geocoded` is called twice with the same `GeocodedPlace.osm_place_id` before commit
- **THEN** both calls succeed without `IntegrityError` and return the same destination `id`

#### Scenario: Counters preserved on conflict

- **WHEN** an existing destination has non-zero `place_count` and upsert runs again for the same `osm_place_id`
- **THEN** `place_count` (and enriched/indexed counts) remain unchanged by the upsert SET clause

### Requirement: Destination name search in repository

The system SHALL provide `DestinationRepository.search_by_name(query, *, limit=10)` that strips whitespace, matches `name` OR `display_name` with case-insensitive ILIKE, and orders by `place_count` descending then `name` ascending.

#### Scenario: ILIKE match

- **WHEN** a destination named "Darjeeling" exists and `search_by_name("darj")` is called
- **THEN** that destination appears in the result list (subject to limit)

### Requirement: Cache-aside destination search service

The system SHALL provide `DestinationService.search(query)` that: (1) returns `repo.search_by_name` results when non-empty without calling geocode; (2) on empty DB results calls `geocode(query)` from `src.geo.geocoder` only; (3) if geocode returns `None`, raises `DestinationNotFoundError(query=query)`; (4) otherwise atomic-upserts, commits, refreshes, and returns `[dest]`. The service MUST NOT import httpx. `get_by_id` MUST raise `DestinationNotFoundError` when missing (not only generic `NotFoundError`).

#### Scenario: DB hit skips Nominatim

- **WHEN** a matching destination already exists in the database
- **THEN** `search` returns it without requiring a live Nominatim round-trip for that query path

#### Scenario: Geocode miss is 404 domain error

- **WHEN** DB search is empty and `geocode` returns `None`
- **THEN** `DestinationNotFoundError` is raised with the query in details

#### Scenario: Geocode miss path commits upsert

- **WHEN** DB search is empty and geocode returns a `GeocodedPlace`
- **THEN** the destination is upserted, the session is committed, and a subsequent search returns the same `id`
