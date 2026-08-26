## Purpose

Evidence-gathering diagnostics for hybrid place search: record dense vs sparse vs fused hit order in planner `tool_trace` without changing which places are returned for planning.

## Requirements

### Requirement: Fusion diagnostics capture search mode and hit orders
When fusion diagnostics are enabled via settings, each successful or empty Qdrant-backed place search MUST produce a diagnostics object that includes at least: search mode (`hybrid_rrf`, `dense_only`, or `unavailable`), collection name in use, whether sparse was enabled for the query, and ordered place_id lists for the fused result used for candidates. When the hybrid RRF path runs, the diagnostics MUST also include ordered place_id lists for dense-only and sparse-only candidate orders (same destination filter and comparable limit), unless a fail-soft diagnostic subquery fails — in which case those lists MAY be omitted or empty while fused results for planning remain unaffected.

#### Scenario: Hybrid search records three orders
- **WHEN** diagnostics are enabled and hybrid RRF search returns fused hits
- **THEN** diagnostics include mode `hybrid_rrf`, a fused place_id order, and dense and sparse place_id orders (when those subqueries succeed)

#### Scenario: Dense-only path still records diagnostics
- **WHEN** diagnostics are enabled and search uses dense-only (sparse off or unavailable)
- **THEN** diagnostics include mode `dense_only`, fused/dense place_id order from the results used for candidates, and do not require sparse subquery success

#### Scenario: Diagnostics failure does not empty search hits
- **WHEN** the primary search returns hits but a diagnostic subquery raises or times out
- **THEN** the place search still returns those hits and diagnostics omit or soft-fail the failed lists without raising

### Requirement: Diagnostics are settings-gated and additive only
The system SHALL expose a settings flag (via `get_settings()`) to enable or disable fusion diagnostics. Disabling diagnostics MUST restore the prior search behavior for result lists (no extra diagnostic queries required). Diagnostics MUST NOT change HTTP paths, SSE event names, or trip DTO envelopes. Diagnostics MUST NOT be required for generate success.

#### Scenario: Kill-switch disables diagnostic queries
- **WHEN** the diagnostics settings flag is false
- **THEN** search returns the same candidate ordering contract as V5 without requiring diagnostic subqueries

#### Scenario: Generate succeeds with diagnostics off or on
- **WHEN** place search runs during generate with diagnostics enabled or disabled
- **THEN** generation is not failed solely due to missing or partial diagnostics
