## ADDED Requirements

### Requirement: ToolTraceEntry MAY carry optional fusion diagnostics
`ToolTraceEntry` MUST remain backward compatible for existing fields (`name`, `ok`, `ms`, `phase`, `code`, `fallback_used`). It MAY include an optional diagnostics field (dict or structured optional payload). When `apply_tool_result` processes a `ToolResult` whose data contains fusion diagnostics, it MUST copy that payload onto the appended `tool_trace` entry. Fusion diagnostics MUST NOT be added to TravelState merge keys used for planning fields such as `candidate_pois`.

#### Scenario: Diagnostics land on tool_trace entry
- **WHEN** `apply_tool_result` runs for `search_places` with `fusion_diagnostics` in `ToolResult.data`
- **THEN** the new `tool_trace` entry includes that diagnostics payload and `candidate_pois` merge behavior is unchanged

#### Scenario: Missing diagnostics keeps prior trace shape
- **WHEN** `apply_tool_result` runs for a tool without fusion diagnostics in data
- **THEN** a `tool_trace` entry is still appended with existing required fields and without requiring a diagnostics value
