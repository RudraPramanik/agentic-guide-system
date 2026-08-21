## ADDED Requirements

### Requirement: build_route fails closed on empty place set
`build_route` MUST return `ok=False` (stable code such as `no_ranked_places`) when both `ranked_pois` and `candidate_pois` are empty, and MUST NOT write a successful empty multi-day `route` that later looks like progress. When candidates exist but ranked is empty, it MAY auto-rank from candidates as today and then route. Fake routing tests with a non-empty ranked set MUST still return `ok=True` without live OSRM.

#### Scenario: Empty ranked and candidates is not ok
- **WHEN** `build_route` runs with empty `ranked_pois` and empty `candidate_pois`
- **THEN** `ToolResult.ok` is False and state MUST NOT be treated as a successful PLAN route

#### Scenario: Fake routing works in tests
- **WHEN** `build_route` is invoked with a FakeRoutingProvider and a non-empty ranked set
- **THEN** it returns `ok=True` (or documented soft-fail codes) without calling live OSRM and never raises
