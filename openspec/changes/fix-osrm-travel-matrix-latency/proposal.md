## Why

P5.14 live smoke (`scripts/test_agent.py`) fails with `generation_timeout` even when NVIDIA NIM is healthy: after discover tools run, `build_route` → `OsrmRoutingProvider.travel_matrix` issues **sequential** pairwise `get_route` calls (O(n²)). Against public OSRM that burns the planner wall clock (often 300s) before any schedule is produced. Unblocking P5 ship (and honest P6 gate) requires fixing routing matrix latency — not swapping LLM providers again.

## What Changes

- Make `OsrmRoutingProvider.travel_matrix` **concurrent** (bounded parallelism) over the same pairwise `geo.osrm.get_route` contract — no new OSRM endpoint type required for MVP.
- Cap concurrency via `get_settings()` (new setting; default safe for public `router.project-osrm.org`).
- Keep per-leg haversine fallback behavior from `get_route` (never raise; `used_fallback` still propagates to `RouteLeg`).
- Add/extend unit tests proving matrix completion with a slow Fake/stub provider finishes under a concurrency budget (no live OSRM required for CI).
- Re-run `scripts/test_agent.py` after the fix to unblock `ship-p5-14-smoke-nvidia-nim` (separate change; this change does not stamp P5 complete by itself).

**Non-goals:** self-hosted OSRM/Valhalla; OSRM `/table` API migration; changing `travel_engine` purity or `RoutingProvider` call sites; LLM/gateway changes; raising `PLANNER_GENERATION_TIMEOUT_SECONDS` as the primary “fix”; P6 HTTP SSE.

## Capabilities

### New Capabilities

- `osrm-travel-matrix-concurrency`: Bounded-parallel pairwise travel matrix in `OsrmRoutingProvider` so day optimization completes within planner generation timeouts under public OSRM latency.

### Modified Capabilities

- `planner-routing-provider`: Require bounded-concurrent pairwise `get_route` in `travel_matrix` (same leg semantics; no longer effectively serial-only).

## Impact

- **Code:** `src/planner/routing_provider.py` (primary); `src/config.py` + `.env.example` for concurrency setting; tests under `tests/planner/` or `tests/geo/`.
- **AGENT.md:** Geo only via `src/geo/`; all env via `get_settings()`; every httpx path already has timeouts/retries/fallback in `geo/osrm.py` — provider must not bypass that.
- **Blueprint:** Public OSRM MVP + haversine fallback unchanged; Strategy/DI via `RoutingProvider` preserved.
- **Downstream:** Unblocks P5.14 smoke wall-clock; reduces false `generation_timeout` aborts when LLM is fine.
- **Risk:** Too-high concurrency may rate-limit public OSRM → mitigate with low default semaphore + existing per-call fallback.
