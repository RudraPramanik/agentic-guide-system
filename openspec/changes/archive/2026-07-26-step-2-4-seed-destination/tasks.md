## 1. Implement seed CLI

- [x] 1.1 Replace stub `scripts/seed_destination.py` with argparse CLI (`--destination` required, `--radius` default 30) + `configure_logging()` / `get_logger()`
- [x] 1.2 Implement async seed flow: `geocode` → exit 1 if None → `DestinationRepository.upsert_from_geocoded` → `fetch_pois` → per-POI `upsert_from_poi` with try/except continue + progress every 10
- [x] 1.3 After POI loop: `update(dest.id, {"place_count": success_count})`, `session.commit()`, print `Seeded {success}/{total} places for {name} (id={dest_id})`; Overpass `[]` → warning + `place_count=0` + commit

## 2. Validate

- [x] 2.1 Live seed: `python scripts/seed_destination.py --destination "Darjeeling" --radius 30` (expect n ≥ 50 + UUID; Postgres + network)
- [x] 2.2 Re-run same command — same destination id, no duplicate places
- [x] 2.3 Nonsense geocode: `--destination "XyzzyNonexistentPlace99999"` → non-zero exit
- [x] 2.4 Run step 2.4 mocked single-POI failure loop (`python -c` from step doc) → PASS continue pattern (step doc snippet was buggy — missing `self` param; fixed in `docs/steps/step2.md`, plus a real `seed_places()` savepoint proof)

## 3. Context checkpoint

- [x] 3.1 Update `docs/context.md`: 2.4 ✅, Next → **2.5**, Implemented modules/scripts row for seed CLI, stubs note
- [x] 3.2 Manual refresh (cadence hit — 4 validated steps since the P2.2 marker): `docs/app/documentation.md`, `docs/manual/01|03|04|05|06`
- [x] 3.3 Step-doc corrections in `docs/steps/step2.md` §2.4: savepoint-per-POI rule, `seed_places()` extraction, fixed the failure-path-2 snippet (missing `self`), added a real-transaction failure path 3
