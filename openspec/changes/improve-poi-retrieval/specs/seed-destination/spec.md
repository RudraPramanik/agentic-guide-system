## MODIFIED Requirements

### Requirement: Seed destination CLI pipeline

The system SHALL provide `scripts/seed_destination.py` that accepts `--destination` (required) and `--radius` (km, default 30), then: geocodes via `geocode`, atomically upserts the destination via `DestinationRepository.upsert_from_geocoded`, fetches POIs via the geo places-provider facade, upserts each POI via `PlaceRepository.upsert_from_poi`, updates `place_count` to the success count via `BaseRepository.update`, and commits. The script MUST NOT call Nominatim, Overpass, OpenTripMap, Geoapify, or httpx directly.

#### Scenario: Seed Darjeeling successfully

- **WHEN** `python scripts/seed_destination.py --destination "Darjeeling" --radius 30` runs with network + Postgres available and Overpass (or configured sources) available
- **THEN** a destination row exists, at least 50 places are upserted for that destination, and stdout reports seeded counts plus the destination UUID

#### Scenario: Re-run is idempotent

- **WHEN** the same seed command is run twice for Darjeeling
- **THEN** the destination id is unchanged and place rows are not duplicated by `osm_id` (place count remains stable)

### Requirement: Seed failure boundaries

The seed script SHALL treat geocode failure as fatal (exit code 1, no commit). Empty places-facade results SHALL still persist the destination with `place_count=0` and emit a warning (exit 0). A single place upsert failure SHALL be logged and skipped; the batch MUST continue and the final count MUST reflect successes only.

#### Scenario: Nonsense destination exits 1

- **WHEN** seed is run with a nonexistent place name that geocodes to `None`
- **THEN** the process exits non-zero and does not commit a successful seed

#### Scenario: Empty Overpass still saves destination

- **WHEN** the places facade returns `[]` (including when Overpass-only retrieval is empty)
- **THEN** the destination row is committed with `place_count=0` and a warning is printed or logged

#### Scenario: Single POI failure does not abort batch

- **WHEN** one of several POI upserts raises during the seed loop
- **THEN** remaining POIs are still attempted and the success count excludes the failed POI

### Requirement: Seed pipeline is callable from destination prepare

The seed pipeline (geocode-or-existing-point → places facade → per-POI upsert → `place_count` update) MUST remain usable from the CLI **and** from destination prepare. `upsert_from_geocoded` MUST still never write `place_count`, `enriched_count`, or `indexed_count`. Prepare MUST update `place_count` only through the seed pipeline’s counter update (same as the CLI). CLI flags `--destination` / `--radius` and CLI failure boundaries (geocode miss → exit 1; empty facade → destination with `place_count=0`; single POI skip) MUST remain.

#### Scenario: CLI seed still works

- **WHEN** an operator runs `python scripts/seed_destination.py --destination "Darjeeling" --radius 30`
- **THEN** the destination is seeded as today (idempotent re-run, no duplicate `osm_id` rows)

#### Scenario: HTTP prepare uses the same place upsert rules

- **WHEN** prepare seeds POIs for a destination
- **THEN** each POI is upserted without duplicating `osm_id`, a single POI failure does not abort the batch, and `place_count` reflects successes only
