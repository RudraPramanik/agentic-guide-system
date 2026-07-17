## 1. Config + dependencies

- [x] 1.1 Append to `requirements.txt` with why-comments: `python-jose[cryptography]==3.5.0`, `email-validator==2.3.0`, `httpx==0.28.1`; install them
- [x] 1.2 Extend `Settings` in `src/config.py`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `ACCESS_TOKEN_EXPIRE_DAYS`, `GOOGLE_AUTH_URL`, `GOOGLE_TOKEN_URL`, `GOOGLE_USERINFO_URL` (safe defaults)

## 2. Step 1.6 — JWT + permissions

- [x] 2.1 Implement `src/core/security/jwt.py` — `TokenPayload`, `create_access_token`, `verify_token` (never raises; TTL from settings)
- [x] 2.2 Implement `src/core/security/permissions.py` — shared token extract (Bearer then `wandr_token` cookie), `require_auth`, `optional_auth`, `get_current_user_id`
- [x] 2.3 Run step 1.6 JWT validation script (valid / invalid / expired → PASS)

## 3. Step 1.7a — schemas + exceptions

- [x] 3.1 Implement `src/auth/schemas.py` — `UserOut`, `AuthMeResponse`, `TokenResponse`, `GoogleCallbackParams`
- [x] 3.2 Implement `src/auth/exceptions.py` — `GoogleOAuthError`, `InvalidTokenError`, `AccountInactiveError`
- [x] 3.3 Run step 1.7a validation script (guest response + exception hierarchy → PASS)

## 4. Step 1.7b — repository + service

- [x] 4.1 Implement `src/auth/repository.py` — `UserRepository` with `get_by_email`, `get_by_google_id`
- [x] 4.2 Implement `src/auth/service.py` — `upsert_google_user` (commit), `get_user_by_id`, Google exchange/userinfo with timeouts + tenacity + settings URLs
- [x] 4.3 Run step 1.7b validation script (import + instantiate → PASS)

## 5. Step 1.7c — router + wiring

- [x] 5.1 Implement `src/auth/router.py` — `/google`, `/callback`, `/me`, `/logout` per design (single AuthService, httpOnly session cookie, cookie+Bearer auth)
- [x] 5.2 Register auth router in `src/main.py` under the routers comment block
- [x] 5.3 Validate with uvicorn: curl guest `/me`, `/logout`, `/google` (not configured) match expected `ApiResponse` shapes

## 6. Context checkpoint

- [x] 6.1 Update `docs/context.md` — mark 1.6 and 1.7a–c done, Next step **1.8**, add implemented modules, note live auth endpoints
