## 1. Context gate + developer manual index

- [ ] 1.1 Confirm Through-step target from `docs/context.md` (expect P7.6 / post-P7 + Next operator VPS deploy via `docs/steps/blueprint_production.md`; if any P7 row still incomplete, Through-step ≤ highest ✅ step — do not claim unfinished modules)
- [ ] 1.2 Bump `docs/app/documentation.md` to Through step **P7.6** (or gated/post-P7 target), refresh date, read-order “next” hint (operator deploy), and snapshot (P7 edit HTTP + `populate_leg_polylines` + day surgery + `rate_limit_trip_edit` + eval flag polish + `scripts/test_p7_smoke.py` + pytest ~248; production packaging / hosted embeddings one-liner; stubs = evaluation HTTP + `auth/dependencies.py`)
- [ ] 1.3 Add P7 phase-complete / catch-up row to `docs/manual/06-maintenance.md` refresh log; update “next natural refresh” to the next cadence trigger (post-deploy docs, or ~4–5 validated steps)

## 2. Module map, layers, wiring, recipes

- [ ] 2.1 Update `docs/manual/03-module-map.md` through P7: mark trip edit routes, `populate_leg_polylines`, TripService day surgery + preserve-order + TripEditEvent UoW, `rate_limit_trip_edit`, evaluation `mark_trip_edited` polish, `tests/trips/test_edit_replan.py`, `scripts/test_p7_smoke.py` as real when context says ✅; clear residual “P7 later / edit unbuilt” framing; keep evaluation HTTP and `auth/dependencies.py` stub-explicit
- [ ] 2.2 Update `docs/manual/04-imports-and-wiring.md` for trips edit router → `rate_limit_trip_edit` → TripService edit ops → repo/`populate_leg_polylines`/schedule preserve-order; evaluation flag polish path; main.py already-registered edit routes
- [ ] 2.3 Update `docs/manual/05-how-to-change.md` with P7 verification recipes (`pytest` edit/replan + flag tests, `scripts/test_p7_smoke.py`); document the four live edit endpoints + auth/ownership + user-keyed rate limit; point deploy/FE readers at `blueprint_production.md` / `FE_guide.md` without inventing evaluation HTTP
- [ ] 2.4 Skim `docs/manual/01-orientation.md` and `02-layers.md` for stale “P7 next / edit unbuilt / through P6.5” claims; fix only factual drift

## 3. Architecture light touch (`system.md` / `lld.md`)

- [ ] 3.1 Scan `docs/app/system.md` for concrete post-P7 factual drift (trips “edit/replan HTTP later (P7)”, Build Progress stuck at P6.5, MiniLM-only lifespan framing without hosted embeddings path); apply minimal corrections only (no architecture rewrite); link `blueprint_production.md` for deploy topology
- [ ] 3.2 Scan `docs/app/lld.md` for missing shipped P7 patterns (trip edit UoW, preserve-order schedule, user-keyed trip-edit rate limit, public `populate_leg_polylines`); mark present; no essay rewrite

## 4. Sanity check

- [ ] 4.1 Run the `06-maintenance.md` sanity checklist against `docs/context.md` (implemented vs stubs; no stub API recipes; no invented evaluation HTTP live routes)
- [ ] 4.2 Confirm no doc under `docs/app/` or `docs/manual/` still claims trip edit/replan HTTP is unbuilt, or that next build step is P7.*
