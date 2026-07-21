## Why

Steps 1.9–1.12 close P1 before P2 geo work. The user asked whether these steps need changes for **production-grade reliability, updated packages, simplicity, scalability, and error boundaries**. A focused review shows the blueprint/step prompts are **already strong on failure boundaries** (rate limit fail-open, smoke test rollback, migration additive-only). A few **targeted amendments** are needed — not a rewrite and **not a bulk package upgrade** during P1 finish.

## What Changes

### Verdict by step

| Step | Keep as-is | Amend |
|------|------------|-------|
| **1.9** TripEditEvent | Model schema, migration 003, no new packages | Add failure proof: re-run `alembic upgrade head` idempotent; register model in test conftest imports |
| **1.10** Rate limit | Fail-open, 429 + Retry-After, sliding window, planner 10/min | Move limits to `config.py`; add `RateLimiterBackend` protocol (InMemory now, Redis P6); optional stale-key cleanup for long-running dev |
| **1.11** pytest | conftest already **better** than prompt (TRUNCATE isolation) | Add deferred header tests + **failure-path** tests (fail-open, 429 burst); skip re-install if packages present; import `TripEditEvent` after 1.9 |
| **1.12** smoke test | 5-section script, rollback, SystemExit on failure | Add **§6 TripEditEvent** FK/cascade check; only new package: `shapely==2.1.2` |

### Explicit non-changes

- **No bulk upgrade** of FastAPI, SQLAlchemy, litellm, etc. during 1.9–1.12 — violates blueprint "packages at point of use" and adds regression risk. Pin `structlog` in a separate hygiene change if desired.
- **No Redis rate limiter in P1** — P6 via `REDIS_URL`; 1.10 stays in-memory with documented single-worker limit.
- **No rewrite of blueprint** — amendments go into `docs/steps/step1.md` and implementation.

## Capabilities

### New Capabilities

- `p1-step-amendments`: Documented amendments to steps 1.9–1.12 for config-driven limits, failure tests, and smoke coverage.

### Modified Capabilities

- `rate-limit-middleware`: Limits from settings; backend protocol; fail-open test required.
- `trip-edit-event`: Conftest registration + smoke test insert.
- `pytest-harness`: Failure-path rate limit tests; middleware header asserts after 1.10.

## Impact

| Area | Impact |
|------|--------|
| `docs/steps/step1.md` | Patch sections 1.9–1.12 with amendments |
| `src/config.py` | Add rate limit settings (defaults match current hardcoded values) |
| `src/core/middleware/rate_limit.py` | Protocol + config-driven limits |
| `tests/` | Header + failure tests for rate limit |
| `scripts/test_p1_smoke.py` | New file + TripEditEvent section |
| `requirements.txt` | `shapely==2.1.2` only (pytest already pinned) |
