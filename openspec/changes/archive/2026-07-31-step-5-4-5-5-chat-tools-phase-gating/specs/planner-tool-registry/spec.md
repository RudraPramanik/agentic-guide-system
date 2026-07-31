## ADDED Requirements

### Requirement: execute_tool bookkeeping via orchestration
After step 5.5, callers that apply tool outcomes MUST use `apply_tool_result` (registry orchestration) so that every `execute_tool` dispatch whose name resolves in `TOOL_REGISTRY` results in exactly one `tool_loop_count` increment and one `tool_trace` entry, including `precondition_failed` outcomes. Unregistered names (`unknown_tool`) MUST NOT increment `tool_loop_count`.

`execute_tool` itself MUST continue to soft-fail (never raise), reject wrong-phase before calling `fn`, and MUST NOT merge `ToolResult.data` into route/schedule — that remains `apply_tool_result`’s job.

#### Scenario: Wrong-phase rejects without calling fn
- **WHEN** `execute_tool("build_route", ...)` runs while `agent_phase` is DISCOVER
- **THEN** the result has `ok=False` and `code="precondition_failed"` and the tool body is not invoked (spy/mock call count == 0)

#### Scenario: Resolved name bookkeeping on apply
- **WHEN** `execute_tool` returns `precondition_failed` for a registered tool and `apply_tool_result` is invoked
- **THEN** `tool_loop_count` increments by one and a `tool_trace` entry is appended
