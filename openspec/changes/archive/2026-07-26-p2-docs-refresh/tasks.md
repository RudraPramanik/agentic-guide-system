## 1. Developer manual index + maintenance

- [x] 1.1 Bump `docs/app/documentation.md` to Through step **P2.10**, refresh date, read-order “next” hint (P3.1), and snapshot (pytest + smoke present; next = P3+)
- [x] 1.2 Add P2 phase-complete row to `docs/manual/06-maintenance.md` refresh log; update “next natural refresh” to the next cadence trigger

## 2. Module map, wiring, recipes

- [x] 2.1 Update `docs/manual/03-module-map.md` through P2.10: mark OSRM, destinations/places HTTP, readiness, `tests/geo|destinations|places|scripts`, `scripts/test_p2_smoke.py`, `seed_destination_into` as real; keep planner/search/travel_engine/trips stubs explicit
- [x] 2.2 Update `docs/manual/04-imports-and-wiring.md` so P2 tests/smoke/`seed_destination_into` are documented as landed (remove “lands in 2.9–2.10” wording)
- [x] 2.3 Update `docs/manual/05-how-to-change.md` seed/readiness recipe with formula-true floors (volume ≥50 vs limited-band ≥100 preferred) and mention `python scripts/test_p2_smoke.py` / `pytest` P2 packages where appropriate
- [x] 2.4 Skim `docs/manual/01-orientation.md` and `02-layers.md` for stale “P2 incomplete” / stub claims; fix only factual drift

## 3. P2 study guide + architecture light touch

- [x] 3.1 Rewrite `docs/app/p2guide.md` “stubs / You are here / target endpoints” sections for P2-complete present tense; point next phase at P3.1
- [x] 3.2 Align readiness / interview Q&A in `p2guide.md` with formula-true floors (`50` sparse; limited needs higher place_count)
- [x] 3.3 Scan `docs/app/system.md` and `docs/app/lld.md` for concrete post-P2 factual drift; apply minimal corrections only (no architecture rewrite)

## 4. Sanity check

- [x] 4.1 Run the `06-maintenance.md` sanity checklist against `docs/context.md` (implemented vs stubs; no stub API recipes)
- [x] 4.2 Confirm no doc still claims 2.9/2.10 are unbuilt or that geo/destinations/places are stubs
