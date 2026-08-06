## 1. Preflight (perfect start for 7.0)

- [x] 1.1 Re-read `AGENT.md`, `docs/context.md`, and `docs/steps/step7.md` §7.0 only — confirm P6.5 ✅ and do **not** implement 7.1–7.6 in this change
- [x] 1.2 Confirm gate: `RoutingProvider.route_polyline` exists; `save_from_state` currently omits `base_lat`/`base_lng` in preferences (baseline)

## 2. Implement persist + resolve

- [x] 2.1 Extend `TripService.save_from_state` preferences: when both `base_lat` and `base_lng` coerce to float, store them; otherwise omit both keys; keep existing preference keys
- [x] 2.2 Add `_resolve_base(trip, destination) -> tuple[float, float]` — prefs win for non-bool `int`/`float` pair; else destination; never raise on bad prefs
- [x] 2.3 Brief docstring note: pre-7.0 trips fall back to destination centroid (MVP limitation)

## 3. Tests

- [x] 3.1 Extend `tests/trips/test_save_from_state.py` (or focused module): save with base_* → preferences contain floats
- [x] 3.2 Test save without base_* → trip saved; preferences omit base keys
- [x] 3.3 Unit tests for `_resolve_base`: prefs-win, destination-fallback, non-numeric/bool → destination
- [x] 3.4 Run `python -m pytest tests/trips/ -v` green (and full suite if time: `python -m pytest tests/ -v`)

## 4. Context ship (7.0 only)

- [x] 4.1 Update `docs/context.md`: Last updated; Progress **7.0** ✅; Next step **7.1**; one-liner note base prefs + `_resolve_base`; do **not** claim edit HTTP done or clear “P7 still stubs” for full P7
