## ADDED Requirements

### Requirement: Allocator V2 is an injected mode after comparison
`allocate_days` MUST accept an injected mode parameter that defaults off. The module MUST NOT call `get_settings()` and MUST NOT contain `TRAVEL_ENGINE_V2_ENABLED` or `VALIDATOR_V2_ENFORCE`. With the mode off or omitted, day membership MUST match the current allocator for the same inputs. With the mode on, each day MUST still satisfy `MAX_PLACES_PER_DAY`, `ACTIVE_DAY_VISIT_BUDGET_MIN`, and at most two morning-only places. A place MUST NOT be added to a day whose centroid is farther than `CLUSTER_RADIUS_KM` when an empty day or a day within that radius can accept it. The implementation MUST NOT add a clustering library. A written comparison of the current allocator against the 10 km radius, the place cap, and the 8 h visit budget (already expressed as `ACTIVE_DAY_VISIT_BUDGET_MIN`) MUST exist before any constant change. If that comparison names no cap or coherence miss, mode-on packing MUST match mode-off packing, and those constants MUST stay unchanged.

#### Scenario: Default call matches today's packing
- **WHEN** `allocate_days` is called without the V2 mode parameter
- **THEN** the day membership matches the current allocator for the same places and day count

#### Scenario: Far cluster does not join a near day
- **WHEN** one day already holds a cluster and another place lies farther than `CLUSTER_RADIUS_KM` from that cluster, and an empty day exists
- **THEN** the far place is not placed on the occupied day

#### Scenario: Mode-on days stay inside the caps
- **WHEN** V2 mode is on and more places are offered than one day can hold
- **THEN** every returned day has at most `MAX_PLACES_PER_DAY` places and a visit sum at most `ACTIVE_DAY_VISIT_BUDGET_MIN`

### Requirement: V2 packing does not loosen geographic coherence
On a shared fixture, the geographic coherence kilometer value of a V2 packing MUST be less than or equal to the mode-off packing. A larger kilometer value is a failure. The comparison MUST use the existing coherence metric rather than a second dispersion formula.

#### Scenario: V2 coherence is not worse
- **WHEN** the same selected places are allocated with V2 mode off and on
- **THEN** the mode-on coherence kilometer value is less than or equal to the mode-off value
