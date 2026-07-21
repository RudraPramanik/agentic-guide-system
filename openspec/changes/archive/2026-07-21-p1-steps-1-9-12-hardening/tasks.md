## 1. Update step documentation

- [ ] 1.1 Patch `docs/steps/step1.md` §1.9 — add conftest model import note; idempotent `alembic upgrade head` failure proof
- [ ] 1.2 Patch §1.10 — config.py settings, `RateLimiterBackend` protocol, stale-key cleanup; remove hardcoded limits from example code
- [ ] 1.3 Patch §1.11 — note pytest already installed; keep TRUNCATE conftest; add fail-open + 429 mock tests; defer header tests until after 1.10
- [ ] 1.4 Patch §1.12 — add §6 TripEditEvent insert + CASCADE check

## 2. Implement step 1.9 (with amendments)

- [x] 2.1 TripEditEvent model + migration 003 per `step-1-9-trip-edit-event` change
- [x] 2.2 Add `TripEditEvent`, `EditType` to `tests/conftest.py` model imports
- [x] 2.3 Validate: second `alembic upgrade head` is no-op

## 3. Implement step 1.10 (with amendments)

- [x] 3.1 Add rate limit fields to `src/config.py` and `.env.example`
- [x] 3.2 Implement `RateLimiterBackend` protocol + `InMemoryRateLimiter` + `RateLimitMiddleware` in `src/core/middleware/rate_limit.py`
- [x] 3.3 Register middleware in `src/main.py` (logging outermost)
- [x] 3.4 Validate: curl health shows X-RateLimit-* headers; planner limit assert script passes

## 4. Complete step 1.11 (with amendments)

- [x] 4.1 Add `test_x_request_id_present`, `test_rate_limit_headers_present` to auth or middleware tests
- [x] 4.2 Add `test_rate_limit_fail_open` (mock backend exception → 200)
- [x] 4.3 Add `test_rate_limit_returns_429` (mock backend returns not allowed → 429 + Retry-After)
- [x] 4.4 Run `pytest tests/ -v` — all green

## 5. Implement step 1.12 (with amendments)

- [x] 5.1 Add `shapely==2.1.2` to `requirements.txt`
- [x] 5.2 Create `scripts/test_p1_smoke.py` with sections 1–5 from step1.md plus §6 TripEditEvent
- [x] 5.3 Run smoke script — ALL PASSED
- [x] 5.4 Update `docs/context.md` — P1 complete, next step P2.1

## 6. Explicitly out of scope (do not do in this slice)

- [x] 6.1 ~~Bulk upgrade FastAPI/SQLAlchemy/litellm~~ — separate change if needed
- [x] 6.2 ~~Redis rate limiter~~ — P6 when `REDIS_URL` present
- [x] 6.3 ~~Pin structlog~~ — optional follow-up `deps-pin-structlog`
