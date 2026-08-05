## 1. Context gate + developer manual index

- [x] 1.1 Confirm Through-step target from `docs/context.md` (expect P6.5 + Next P7.1; if any P6 row still incomplete, Through-step ≤ highest ✅ step — do not claim unfinished modules)
- [x] 1.2 Bump `docs/app/documentation.md` to Through step **P6.5** (or gated target), refresh date, read-order “next” hint (P7.1), and snapshot (P5 bridge/smoke catch-up + P6 polylines/trips HTTP/planner SSE/cache backends + pytest/`scripts/test_p6_smoke.py`; stubs = P7 edit/replan + evaluation HTTP + `auth/dependencies.py`)
- [x] 1.3 Add P6 phase-complete / P5+P6 catch-up row to `docs/manual/06-maintenance.md` refresh log; update “next natural refresh” to the next cadence trigger (P7 phase end or ~4–5 steps)

## 2. Module map, layers, wiring, recipes

- [x] 2.1 Update `docs/manual/03-module-map.md` through P6: mark trips HTTP/GeoJSON/claim, planner SSE generate, `core/cache/backends`, Redis/InMemory rate limiter, polylines, `tests/trips` + cache/SSE tests, `scripts/test_p6_smoke.py` as real when context says ✅; clear residual P5.12–5.14 stub framing; keep P7 edit/replan, evaluation HTTP, `auth/dependencies.py` stub-explicit
- [x] 2.2 Update `docs/manual/04-imports-and-wiring.md` for planner router → service → save_from_state/cache, trips router → service → repo, rate limiter / cache backend selection on `REDIS_URL`, main.py router registration
- [x] 2.3 Update `docs/manual/05-how-to-change.md` with P6 verification recipes (`pytest` trips/cache/SSE, `scripts/test_p6_smoke.py`); SSE client notes (POST `fetch()`, proxy buffering off); empty `REDIS_URL` in-memory caveat; explicitly note P7 edit/replan is not live
- [x] 2.4 Skim `docs/manual/01-orientation.md` and `02-layers.md` for stale “trips HTTP stub / planner generate lands in P6 / next is P5.12” claims; fix only factual drift

## 3. Architecture light touch (`system.md` / `lld.md`)

- [x] 3.1 Scan `docs/app/system.md` for concrete post-P6 factual drift (trips “HTTP CRUD later”, planner “HTTP generate P6” as future-only, Build Progress stuck at P5.11); apply minimal corrections only (no architecture rewrite)
- [x] 3.2 Scan `docs/app/lld.md` for Cache-Aside “planner cache later” and missing Redis/InMemory rate-limiter / Strategy framing; mark shipped patterns present; no essay rewrite

## 4. Sanity check

- [x] 4.1 Run the `06-maintenance.md` sanity checklist against `docs/context.md` (implemented vs stubs; no stub API recipes; no invented P7 edit/replan live routes)
- [x] 4.2 Confirm no doc under `docs/app/` or `docs/manual/` still claims trips HTTP / planner generate / planner cache are unbuilt, or that next build step is P5.12–P6.*
