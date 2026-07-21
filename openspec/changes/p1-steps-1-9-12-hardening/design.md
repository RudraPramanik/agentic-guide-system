## Context

**Current state:** 1.8 done. 1.9–1.12 pending. 1.11 **partially ahead of prompt** — pytest packages installed, `conftest.py` with TRUNCATE isolation, auth tests exist; missing rate-limit middleware and header/failure tests. `structlog` unpinned in requirements (pre-P1 debt).

**Review criteria:** production error boundaries, package reliability, simplicity, scalability.

## Goals / Non-Goals

**Goals:**

- Confirm 1.9–1.12 are safe to implement with minor hardening.
- Centralize rate limit tunables in `get_settings()` per AGENT.md.
- Add verifiable failure proofs before P2.
- Keep P1 scope minimal — one new runtime dependency (`shapely` at 1.12).

**Non-Goals:**

- Bulk dependency upgrades.
- Redis backend implementation (P6).
- Ops runbooks / alerting.

## Decisions

### D1 — Steps are production-oriented; amendments not rewrites

**Decision:** Implement 1.9–1.12 with the amendments in this change. Do not block P1 on a full step1.md rewrite.

**Rationale:** Blueprint Failure Boundary Summary + step 🚨 markers already cover JWT 401, OAuth 502, limiter fail-open, DB rollback. Gaps are config hygiene and test coverage.

### D2 — Rate limit settings in config.py

**Decision:** Add to `Settings`:

```python
RATE_LIMIT_DEFAULT_REQUESTS: int = 60
RATE_LIMIT_DEFAULT_WINDOW_SECONDS: int = 60
RATE_LIMIT_PLANNER_REQUESTS: int = 10
RATE_LIMIT_PLANNER_WINDOW_SECONDS: int = 60
```

Middleware reads via `get_settings()` — no module-level magic numbers.

**Alternative rejected:** Keep hardcoded in middleware — violates AGENT.md "all constants in config.py".

### D3 — RateLimiterBackend protocol (simple, P6-ready)

**Decision:**

```python
class RateLimiterBackend(Protocol):
    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]: ...
```

`InMemoryRateLimiter` implements it now. P6 adds `RedisRateLimiter` when `REDIS_URL` set — same interface, no middleware rewrite.

**Rationale:** Scalability path without over-engineering P1.

### D4 — In-memory limiter memory bound

**Decision:** After each `is_allowed` call, drop empty keys from `_windows` dict (cheap cleanup).

**Rationale:** Long-running dev server with many IPs won't grow unbounded. Not needed for prod Redis path.

### D5 — Package policy for 1.9–1.12

| Package | Action |
|---------|--------|
| pytest / pytest-asyncio / pytest-mock | **Keep pinned** — already in requirements at 9.1.0 / 1.4.0 / 3.15.1 |
| shapely | **Add** at 1.12 only — `shapely==2.1.2` |
| structlog | **Defer** pin to separate `deps-pin-structlog` change — not blocking P1 |
| All other deps | **No upgrade** during P1 finish |

**Rationale:** Current pins are recent and tested; bulk upgrades belong in a dedicated CI-green upgrade PR.

### D6 — 1.11 failure tests (error boundaries)

Add after 1.10 middleware lands:

1. `test_x_request_id_present` — header on health
2. `test_rate_limit_headers_present` — X-RateLimit-* on health
3. `test_rate_limit_fail_open` — mock `is_allowed` to raise; expect 200 not 500
4. `test_rate_limit_returns_429` — burst requests to a test-only low limit OR mock limiter returning False

Prefer mock for 429 test — avoids flaky timing in CI.

### D7 — 1.12 TripEditEvent smoke section

Insert trip + place + `TripEditEvent(edit_type=REORDER, payload={})`; verify row exists; delete trip → cascade removes edit events; rollback.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| In-memory limiter wrong for multi-worker prod | Document in middleware docstring; P6 Redis |
| conftest create_all vs Alembic drift | 1.12 smoke validates migration state |
| Amendment scope creep | This change patches step1.md only for 1.9–1.12 |

## Migration Plan

1. Apply `step-1-9-trip-edit-event` with conftest import addition
2. Apply 1.10 with config + protocol amendments
3. Complete 1.11 failure/header tests
4. Apply 1.12 with shapely + TripEditEvent smoke
5. Patch `docs/steps/step1.md` to reflect amendments (same PR or follow-up)

## Open Questions

- **Pin structlog now?** Recommend separate tiny change — not required for 1.9–1.12 correctness.
