## Context

See proposal.md — Why. Today `HaversineRoutingProvider.route_polyline` always returns `None`; `OsrmRoutingProvider` does full pairwise HTTP for `travel_matrix`. `populate_leg_polylines` already runs only after order is fixed (≤ N+1 geometry calls). GeoJSON and FE MapLibre already consume LineStrings when present.

## Goals / Non-Goals

**Goals:**
- Default-safe path to persist road polylines without OSRM matrix on generate
- Factory + settings extend with `hybrid`; keep fail-soft geometry
- Docs/operators know regenerate/reoptimize for old trips; cross-link FE/parent changes

**Non-Goals:**
- Self-host OSRM; change GeoJSON schema; FE styling; historical backfill job

## Decisions

1. **Hybrid adapter class in `routing_provider.py`**
   - Reuse haversine matrix logic and OSRM `route_polyline` rules (compose or thin wrapper over existing helpers).
   - Alternative rejected: `ROUTING_BACKEND=osrm` as default — matrix risk to 45s generate + public demo rate limits.

2. **`ROUTING_BACKEND=hybrid` as recommended operator setting for map routes; default stays `haversine` unless docs explicitly flip**
   - Safer rollout: opt-in hybrid via `.env` without surprising existing haversine-only installs.
   - Alternative considered: default `hybrid` immediately — acceptable if documented; prefer opt-in first in tasks unless smoke proves latency OK.

3. **No change to `build_geojson` I/O contract**
   - Geometry at generate/edit time only; GeoJSON stays decode-only.

4. **Resilience**
   - All OSRM via existing `geo/osrm.get_route` (tenacity, timeouts, haversine fallback → polyline `None`).

## Risks / Trade-offs

- [Public OSRM flaky] → Mitigation: fail-soft Point-only; later self-host out of scope
- [Extra N+1 HTTP on optimize/edit] → Mitigation: already bounded; matrix stays free
- [Old trips without polylines] → Mitigation: docs + regenerate/reoptimize
- [Agents apply FE first] → Mitigation: parent vault apply order

## Migration Plan

1. Ship hybrid + tests; document `ROUTING_BACKEND=hybrid`
2. Operators set hybrid locally/staging; generate a new trip; confirm GeoJSON LineStrings
3. Rollback: set `ROUTING_BACKEND=haversine` (Point-only again; no schema migration)

## Open Questions

- Whether to flip **default** to `hybrid` after one successful staging smoke (defer; tasks keep default haversine unless explicitly chosen)
