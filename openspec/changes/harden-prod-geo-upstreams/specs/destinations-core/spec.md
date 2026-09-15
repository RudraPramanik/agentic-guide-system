## MODIFIED Requirements

### Requirement: Cache-aside destination search service

The system SHALL provide `DestinationService.search(query)` that: (1) returns `repo.search_by_name` results when non-empty without calling geocode; (2) on empty DB results calls `geocode(query)` from `src.geo.geocoder` only; (3) if geocode returns `None`, raises `DestinationNotFoundError(query=query)`; (4) if geocode raises `ExternalServiceError`, re-raises it unchanged (MUST NOT map it to `DestinationNotFoundError`); (5) otherwise atomic-upserts, commits, refreshes, and returns `[dest]`. The service MUST NOT import httpx. `get_by_id` MUST raise `DestinationNotFoundError` when missing (not only generic `NotFoundError`).

#### Scenario: DB hit skips Nominatim

- **WHEN** a matching destination already exists in the database
- **THEN** `search` returns it without requiring a live Nominatim round-trip for that query path

#### Scenario: Geocode miss is 404 domain error

- **WHEN** DB search is empty and `geocode` returns `None`
- **THEN** `DestinationNotFoundError` is raised with the query in details

#### Scenario: Geocode upstream failure is not not-found

- **WHEN** DB search is empty and `geocode` raises `ExternalServiceError` for service `nominatim`
- **THEN** that `ExternalServiceError` propagates (search MUST NOT raise `DestinationNotFoundError` for this path)

#### Scenario: Geocode miss path commits upsert

- **WHEN** DB search is empty and geocode returns a `GeocodedPlace`
- **THEN** the destination is upserted, the session is committed, and a subsequent search returns the same `id`
