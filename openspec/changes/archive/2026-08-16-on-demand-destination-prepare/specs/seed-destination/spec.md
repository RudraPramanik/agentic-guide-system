## ADDED Requirements

### Requirement: Seed pipeline is callable from destination prepare

The seed pipeline (geocode-or-existing-point → Overpass → per-POI upsert → `place_count` update) MUST remain usable from the CLI **and** from destination prepare. `upsert_from_geocoded` MUST still never write `place_count`, `enriched_count`, or `indexed_count`. Prepare MUST update `place_count` only through the seed pipeline’s counter update (same as the CLI). CLI flags `--destination` / `--radius` and CLI failure boundaries (geocode miss → exit 1; empty Overpass → destination with `place_count=0`; single POI skip) MUST remain.

#### Scenario: CLI seed still works

- **WHEN** an operator runs `python scripts/seed_destination.py --destination "Darjeeling" --radius 30`
- **THEN** the destination is seeded as today (idempotent re-run, no duplicate `osm_id` rows)

#### Scenario: HTTP prepare uses the same place upsert rules

- **WHEN** prepare seeds POIs for a destination
- **THEN** each POI is upserted without duplicating `osm_id`, a single POI failure does not abort the batch, and `place_count` reflects successes only
