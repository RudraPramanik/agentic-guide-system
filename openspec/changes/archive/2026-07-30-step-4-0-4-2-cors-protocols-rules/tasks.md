## 1. Step 4.0 — CORS

- [x] 1.1 Add `CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]` to `src/config.py`
- [x] 1.2 Document `CORS_ALLOWED_ORIGINS` in `.env.example` (JSON list form)
- [x] 1.3 Register `CORSMiddleware` in `create_app()` per `docs/steps/step4.md` step 4.0 (credentials=True, explicit origins, never `*`)
- [x] 1.4 Run step 4.0 ✅ validation (`get_settings` + `create_app` asserts)
- [x] 1.5 Optional: add a focused TestClient CORS origin assertion (full suite remains 4.9)

## 2. Step 4.1 — protocols

- [x] 2.1 Implement `RouteLeg`, `RoutingProvider`, `legs_to_lookup` in `src/travel_engine/protocols.py` exactly per step 4.1
- [x] 2.2 Run step 4.1 ✅ validation import/lookup script
- [x] 2.3 Confirm no `src.geo` / `httpx` / litellm / qdrant / sqlalchemy imports in `protocols.py`

## 3. Step 4.2 — travel_rules

- [x] 3.1 Implement `src/travel_engine/travel_rules.py` constants + `visit_duration_min` exactly per step 4.2
- [x] 3.2 Run step 4.2 ✅ validation (P2 duration keys, default duration, vocab ⊆ check, no sunrise_point / no trek in durations)
- [x] 3.3 Confirm rules module has no I/O and does not import geo/LLM/DB clients

## 4. Closeout

- [x] 4.1 Update `docs/context.md`: Progress 4.0–4.2 ✅, Implemented modules for CORS + protocols + travel_rules, Next step → 4.3; do not mark full P4 done
- [x] 4.2 Run `python -m pytest tests/ -v` to ensure no regressions from CORS/main changes
