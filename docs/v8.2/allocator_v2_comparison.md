# Allocator V2 comparison (blueprint row 4.3)

Compared `src/travel_engine/day_allocator.py` `allocate_days` to the row before any tune. No engine code was changed for this note.

| Locked rule | Current code | Miss? |
|---|---|---|
| 10 km pre-cluster | `CLUSTER_RADIUS_KM = 10.0`. Clusters and spill stay inside that radius. A cluster farther than 10 km does not join a day that already holds another region; an empty day can take it. | No |
| `MAX_PLACES_PER_DAY` | `6`, enforced in `_can_add` | No |
| 8 h visit budget | `ACTIVE_DAY_VISIT_BUDGET_MIN = 8 * 60 - MIN_TRAVEL_BUFFER_MIN` (450). The 8 h figure is the gross day. The 30-minute buffer is already subtracted. Raising the cap to 480 would loosen a shipped limit. | No |
| Morning-only cap | At most 2 `MORNING_ONLY_CATEGORIES` per day | No |
| New clustering library | Pure haversine in the module | No |

No cap miss and no far-cluster miss. `CLUSTER_RADIUS_KM`, `MAX_PLACES_PER_DAY`, and `ACTIVE_DAY_VISIT_BUDGET_MIN` stay unchanged. `allocate_days(..., v2_enabled=True)` uses the same packing body as the default.
