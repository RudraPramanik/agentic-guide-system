## Context

Implement P4 steps **4.0–4.2** from the locked build contract `docs/steps/step4.md` (disk ~1023 lines; reload IDE if it shows empty). Planner SoT remains `docs/blueprint_final.md` v6.1. Do **not** revise step4, step4-fix, or the blueprint in this change.

Current stubs: `src/travel_engine/protocols.py` and `travel_rules.py` are placeholders. No CORS middleware exists yet. `get_settings()` / `create_app()` are real.

## Goals / Non-Goals

**Goals:**
- Ship CORS (4.0), protocols (4.1), travel_rules (4.2) exactly per step4 prompts.
- Pass each step’s ✅ validation; keep travel_engine pure.
- Bump `docs/context.md` for 4.0–4.2 only; Next step = 4.3.

**Non-Goals:**
- Any further design/doc changes.
- Steps 4.3–4.10.
- Continuing or applying stale `openspec/changes/p4-travel-engine`.

## Decisions

### D1 — Build contract is step4.md only
Copy APIs/constants from step 4.0–4.2 prompts. No reinterpretation of vocabulary, CORS, or protocol shapes.

### D2 — CORS list via pydantic-settings
`CORS_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]`. Document JSON-list form in `.env.example`. Never `*` with credentials.

### D3 — Middleware registration
Add `CORSMiddleware` in `create_app()` using settings; do not hardcode production origins in `main.py`. Do not change cookie SameSite.

### D4 — Protocols stay minimal
`RouteLeg` + `RoutingProvider` + `legs_to_lookup` only. No `TravelTimeMatrix` type. No OSRM adapter here.

### D5 — Rules module is data
Implement the exact constant block from step 4.2 including helper `visit_duration_min`. Cross-check `CATEGORY_WEIGHTS ⊆ PLACE_TAG_VOCAB` in validation/tests, not by importing places into production rules module.

## Risks / Trade-offs

- [Risk] IDE shows `step4.md` as 1 line while disk has full prompt → Mitigation: always read from disk/path before coding.
- [Risk] pydantic-settings env parsing for `list[str]` varies by format → Mitigation: document JSON list in `.env.example`; default works without env.
- [Trade-off] Full CORS pytest suite waits for 4.9 → Acceptable; include at least the step4.0 create_app validation (+ optional TestClient).

## Migration Plan

1. 4.0 settings + middleware + validation  
2. 4.1 protocols + import check  
3. 4.2 travel_rules + validation  
4. Update context.md progress  
5. Rollback: revert the five files; empty CORS list disables cross-origin

## Open Questions

None — step4 locks are sufficient.
