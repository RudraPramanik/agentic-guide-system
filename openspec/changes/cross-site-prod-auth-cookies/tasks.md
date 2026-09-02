## 1. Cookie helpers

- [x] 1.1 Add `_cookie_samesite()` in `src/auth/router.py` (`none` in production, else `lax`)
- [x] 1.2 Use it for `wandr_token` / `wandr_session` set-cookie and logout delete-cookie (with matching secure)

## 2. Planner generate

- [x] 2.1 Import `_cookie_samesite` and apply on generate `wandr_session` Set-Cookie

## 3. Tests & docs

- [x] 3.1 Assert production vs non-production SameSite in auth cookie tests (or unit helper tests)
- [x] 3.2 Note staging cross-origin cookie requirement in `docs/steps/blueprint_production.md` (and brief `docs/vps.md` if useful)

## 4. Proof

- [x] 4.1 Run targeted auth tests (`test_cookie_samesite_production_vs_dev` passed; full router suite needs Postgres)
