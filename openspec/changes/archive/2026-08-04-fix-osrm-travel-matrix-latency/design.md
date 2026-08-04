## Context

P5 planner tools call `optimize_route` → `RoutingProvider.travel_matrix`. Today's `OsrmRoutingProvider` builds an all-pairs directed matrix by **awaiting `get_route` in a nested serial loop**. Public OSRM (`router.project-osrm.org`) is ~1s+ per pair; a day with base+6 stops is 42 pairs (~40s+), and multi-day `build_route` stacks that under `PLANNER_GENERATION_TIMEOUT_SECONDS`. Live P5.14 smoke then fails with `generation_timeout` even when NIM LLM calls succeed in ~2s.

Constraints: Geo only via `src/geo/`; `travel_engine` stays pure; resilience stays in `geo/osrm.py` (timeouts, tenacity, haversine fallback). No new packages preferred.

## Goals / Non-Goals

**Goals:**

- Finish a typical day matrix (≤7 waypoints) in wall time compatible with planner generation (order-of-magnitude faster than serial).
- Preserve exact leg semantics (all i≠j pairs, `used_fallback` mapping).
- Bound concurrency so public OSRM is not stampeded.
- Keep CI green with mocked/`Fake` providers (no live OSRM required for unit proof).

**Non-Goals:**

- Migrating to OSRM `/table` (valuable later; out of this delta).
- Self-hosting OSRM in docker-compose.
- Changing `route_optimizer` algorithm or `MAX_PLACES_PER_DAY`.
- LLM client / timeout “fixes” as a substitute for matrix latency.
- Stamping P5.14 complete (resume `ship-p5-14-smoke-nvidia-nim` after this lands).

## Decisions

1. **Parallelize in `OsrmRoutingProvider`, not in `geo/osrm.get_route`**  
   `get_route` remains a single-route gateway. Matrix fan-out is the provider’s job (matches “adapter owns pairwise expansion”).  
   *Alternative:* OSRM table API in `geo/osrm.py` — better asymptotic cost, but new endpoint, URL/parsing, and resilience surface; defer.

2. **`asyncio.Semaphore` + `asyncio.gather`**  
   Build one coroutine per directed pair; semaphore limits in-flight `get_route` calls; gather preserves completion without changing return shape.  
   *Alternative:* unbounded gather — faster until public OSRM rate-limits; rejected for MVP public endpoint.  
   *Alternative:* `asyncio.TaskGroup` — fine on 3.11+, but semaphore+gather matches existing style and is enough.

3. **Concurrency setting: `OSRM_MATRIX_MAX_CONCURRENCY` via `get_settings()`**  
   Default **8** (tunable). Document in `.env.example`. Never `os.environ.get` in provider.  
   *Alternative:* hardcode 8 — rejected (AGENT.md: no hardcoded knobs that operators need to tune).

4. **No change to per-call fallback**  
   Each pair still goes through `get_route`; failures become haversine legs with `fallback_used=True`. Matrix never raises httpx.

5. **Proof strategy**  
   Unit test: patch `get_route` with an artificial delay + concurrency counter; assert peak in-flight ≤ setting and total wall time ≪ serial baseline for N≥4 waypoints. Optional live smoke remains in P5.14 change.

## Risks / Trade-offs

- [Public OSRM rate-limit / 429 under concurrency] → Mitigation: low default (8); existing tenacity only on Timeout/ConnectError — if RateLimit appears as other errors, `get_route` already falls back; operators can lower concurrency.
- [Same wall-clock still high if every call hits read=10s timeout] → Mitigation: fallback path is local/fast; true hangs should fail open to haversine per contract. If many timeouts, itinerary still builds (worse geometry quality, not abort).
- [Ordering of returned legs changes] → Mitigation: specs require the **set** of i≠j legs with correct ids/metrics, not serial visitation order; optimizer already consumes as a lookup.
- [Scope creep into `/table`] → Mitigation: explicit non-goal; reopen if public OSRM remains too slow after concurrency.

## Migration Plan

1. Add setting + example env comment.
2. Implement semaphore gather in `travel_matrix`.
3. Add concurrency unit test; run planner/geo pytest subset.
4. Manually time a 7-waypoint matrix (optional live).
5. Re-apply / continue `ship-p5-14-smoke-nvidia-nim` smoke.

Rollback: revert provider to serial loop; remove setting (or leave unused).

## Open Questions

- None blocking. Default concurrency 8 is a starting point; tune after one live smoke if public OSRM still flakes.
