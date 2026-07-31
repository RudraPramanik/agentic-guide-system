## ADDED Requirements

### Requirement: write_narrative adds titles and paragraphs only
The project SHALL implement `write_narrative` in `src/planner/graph/nodes/write_narrative.py` as a fixed post-loop bookend that:

- Reads the locked schedule/route structure already on `TravelState`.
- Calls `chat_completion` via `src/core/llm/client.py` for day titles and paragraph text only.
- MUST NOT modify stop order, times, or coordinates.
- MUST strip/ignore any LLM-mentioned `place_id` values that are not present in the schedule.
- On `WandrLLMError`, MUST apply template strings per day and increment `llm_retry_count`.
- Writes combined structure + narrative into `state.itinerary`.

#### Scenario: Narrative LLM failure uses templates
- **WHEN** `chat_completion` raises `WandrLLMError` during narrative
- **THEN** per-day template narrative is written, `llm_retry_count` increases, and stop geometry is unchanged

#### Scenario: Narrative module imports
- **WHEN** `write_narrative` is imported from `src.planner.graph.nodes.write_narrative`
- **THEN** the import succeeds and the callable is non-None

### Requirement: record_evaluation always persists via evaluation service
The project SHALL implement `record_evaluation` in `src/planner/graph/nodes/record_evaluation.py` plus real `src/evaluation/repository.py` and `EvaluationService.record_generation(...)` such that:

- Persist existing `TripEvaluation` fields including `tool_trace`, `tool_loop_count`, `agent_phase_reached`, `readiness_score`, geo/OSRM fallback flags, `abort_triggered`, validation fields, prefs, and timings available on state.
- MUST NOT add new TripEvaluation columns or migrations.
- Prefer a short-lived DB session inside the node/service.
- On DB failure: log, append a warning, and MUST NOT crash the graph uncaught.
- Ranking explain strings remain in `tool_trace` only.

Clarification short-circuit (`needs_clarification → END` without this node) is out of this module’s graph reach; service-level persistence for that path is deferred to step 5.12. When this node runs (including abort after `plan_complete` bookend), persistence MUST still occur.

#### Scenario: Evaluation imports
- **WHEN** `record_evaluation` and evaluation service/repo are imported
- **THEN** imports succeed and are no longer step-0.1 one-line stubs

#### Scenario: DB failure soft-warns
- **WHEN** the evaluation write fails
- **THEN** a warning is recorded / logged and the node does not raise an uncaught exception to the graph
