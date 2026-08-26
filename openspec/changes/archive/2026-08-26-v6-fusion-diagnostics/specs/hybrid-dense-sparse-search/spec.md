## ADDED Requirements

### Requirement: Search MAY attach a fusion diagnostics sidecar
The hybrid or dense-only `search_places` path MUST continue to return destination-filtered `PlaceSearchResult`-compatible hits (or `[]` on failure) exactly as before for planning. When fusion diagnostics are enabled, the search layer MUST also make available a diagnostics sidecar describing mode and hit id orders. The sidecar MUST NOT reorder, filter, or replace the primary result list used by callers for candidate loading. Diagnostic subquery failures MUST be fail-soft and MUST NOT convert a successful primary result into `[]`.

#### Scenario: Primary hits unchanged when diagnostics present
- **WHEN** hybrid search succeeds and diagnostics are attached
- **THEN** the ordered place_id list used for planning matches the fused (or dense-only) primary query results, independent of diagnostic metadata

#### Scenario: Diagnostic error keeps primary results
- **WHEN** the primary query succeeds and a diagnostic subquery fails
- **THEN** `search_places` still returns the primary hits (not an empty list solely due to diagnostics)
