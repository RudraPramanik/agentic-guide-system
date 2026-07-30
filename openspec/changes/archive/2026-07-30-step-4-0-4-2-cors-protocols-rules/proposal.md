## Why

P3 is complete and `docs/steps/step4.md` is the locked P4 build contract. The first implementation batch is steps **4.0–4.2**: CORS so a separate frontend can call the API with credentials, plus the pure-Python routing protocol and corrected `travel_rules` constants that every later travel_engine module depends on. Implementing this cluster now unblocks 4.3+ without reopening design.

## What Changes

- **4.0** — Add `CORS_ALLOWED_ORIGINS` to settings + `.env.example`; register FastAPI `CORSMiddleware` in `create_app()` with `allow_credentials=True` and explicit origins only (never `*`).
- **4.1** — Replace stub `src/travel_engine/protocols.py` with `RouteLeg`, `RoutingProvider` protocol, and `legs_to_lookup`.
- **4.2** — Replace stub `src/travel_engine/travel_rules.py` with v6.1/step4 locked constants + `visit_duration_min()`.
- Run step4 ✅ validation commands for 4.0–4.2; add minimal focused tests if needed for CORS allow-origin (full suite is 4.9).
- Update `docs/context.md` Progress for 4.0–4.2 only (Next step → 4.3); do **not** claim full P4 complete.

**Non-goals:** No edits to `step4.md` / `step4-fix.md` / blueprint; no place_selector through validator (4.3–4.7); no `OsrmRoutingProvider` (4.8); no pytest plan 4.9 / smoke 4.10; no auth SameSite code change; do not use stale `openspec/changes/p4-travel-engine` tasks.

## Capabilities

### New Capabilities

- `cors-middleware`: Credentialed CORS from settings with explicit origin list.
- `travel-engine-protocols`: Pure `RouteLeg` / `RoutingProvider` / `legs_to_lookup` with no I/O.
- `travel-engine-rules`: Structural vs interest vocabulary constants and safe duration lookup.

### Modified Capabilities

<!-- Intentionally empty -->

## Impact

- **Code:** `src/config.py`, `src/main.py`, `.env.example`, `src/travel_engine/protocols.py`, `src/travel_engine/travel_rules.py`.
- **AGENT.md:** env via `get_settings()`; travel_engine purity (no geo/LLM/DB in 4.1–4.2).
- **Docs:** `docs/context.md` incremental progress only.
- **Tests:** step validation snippets; optional small CORS TestClient test; full P4 pytest deferred to 4.9.
- **Build contract:** Implement exactly from `docs/steps/step4.md` steps 4.0–4.2 — no further design changes in this cycle.
