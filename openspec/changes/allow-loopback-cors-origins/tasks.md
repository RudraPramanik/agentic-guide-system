## 1. Settings default

- [ ] 1.1 Set `CORS_ALLOWED_ORIGINS` default in `src/config.py` to `["http://localhost:3000", "http://127.0.0.1:3000"]`. Do not add `*`. Do not hardcode origins in `src/main.py`.
- [ ] 1.2 Update `.env.example` CORS JSON list to the same two origins. Leave the production checklist example as explicit HTTPS.

## 2. Tests

- [ ] 2.1 Extend `tests/core/test_cors_middleware.py` so a public-route request with `Origin: http://127.0.0.1:3000` receives `Access-Control-Allow-Origin: http://127.0.0.1:3000` and credentials true (same pattern as the existing localhost case). Keep the localhost case.
- [ ] 2.2 Assert the **settings default** list contains both loopback origins and not `*`. If local `.env` overrides CORS, patch settings for that assertion so it is deterministic.
- [ ] 2.3 Run `python -m pytest tests/core/test_cors_middleware.py -v` (no Postgres required).

## 3. Docs and stop

- [ ] 3.1 In `docs/FE_guide.md` §4–5, state that local cookies need a matched pair (`localhost:3000`+`localhost:8000` **or** `127.0.0.1:3000`+`127.0.0.1:8000`), that mixing hosts splits `wandr_session`, and that CORS listing both origins does not merge cookie jars. Guest trip GET stays optional auth; do not tell operators to log in to fix session mismatch.
- [ ] 3.2 Stop — do not edit `TripService.assert_can_access`, cookie `SameSite`/`httpOnly`/`secure`, planner generate, or sibling `guideagent-frontend`.
