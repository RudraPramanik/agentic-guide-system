## Purpose

Property tests for the current travel engine that lock §11.6 relations, call the Slice 2.3 coherence metric, and record a failure on today's engine instead of changing that engine.

## Requirements

### Requirement: Property tests do not change the engine
The §11.6 suite MUST live under the travel-engine tests. It MUST NOT add or edit travel-engine source. It MUST NOT import a provider SDK, an HTTP client, or a database session. Where a test needs routing responses, it MUST use the existing in-test fake routing provider. `pytest tests/travel_engine -v` MUST exit 0. A property that fails on the current engine MUST be reported by name as a finding, and the test MUST be an expected failure that cites that finding. The engine source MUST stay unchanged.

#### Scenario: Suite exits zero without an engine edit
- **WHEN** the travel-engine test suite runs after this change
- **THEN** the process exits 0 and the travel-engine source diff is empty

#### Scenario: A current failure is a named finding
- **WHEN** a property does not hold for the current engine
- **THEN** the suite records that property's name as a finding and does not edit the engine

### Requirement: Determinism and order invariance
The same candidate input and the same routing responses MUST produce the same selected set and the same day assignment on two runs. Shuffling the candidate input order MUST NOT change the selected set or which day each selected place is assigned to. These tests MUST call the existing selector and allocator.

#### Scenario: Two runs match
- **WHEN** the same candidates and the same routing responses are planned twice
- **THEN** the selected set and the day assignment are identical

#### Scenario: Shuffled input keeps the selection
- **WHEN** the same candidates are passed in a different order
- **THEN** the selected set and the day assignment are unchanged

### Requirement: Removal keeps uniqueness and chronology
Removing any one stop from an itinerary that already has unique place ids and non-decreasing start times MUST leave unique place ids and non-decreasing start times. The test MUST apply that removal in the fixture. It MUST NOT add a remove API to the engine.

#### Scenario: One stop removed
- **WHEN** any single stop is removed from a valid itinerary fixture
- **THEN** no place id repeats and the remaining start times are non-decreasing

### Requirement: Coherence does not improve when a distant point is added
The monotonic-coherence property MUST call the geographic coherence metric from the metrics capability. It MUST NOT reimplement the dispersion formula. Adding a coordinate that is farther from the current centroid than every existing coordinate MUST NOT decrease that metric. A lower kilometer value is tighter, so a decrease would be an improvement and MUST fail this property.

#### Scenario: Distant point uses the shared metric
- **WHEN** a day produced by the current allocator gains a coordinate farther from its centroid than every existing point
- **THEN** the coherence metric's kilometer value does not decrease

### Requirement: Budget and schedule properties
No day returned by the current allocator MUST exceed the configured active-time cap or the configured per-day place cap. Start times within a built day MUST be strictly non-decreasing. When a scheduled leg has a matching route leg, the scheduled duration MUST equal that route leg's duration. A violation on the current engine MUST follow the finding rule and MUST NOT change the engine.

#### Scenario: Allocated days respect the caps
- **WHEN** the allocator packs a fixture that fits the configured caps
- **THEN** every returned day is within the active-time cap and the per-day place cap

#### Scenario: Schedule times do not go backwards
- **WHEN** the schedule builder emits a day
- **THEN** each start time is strictly later than the previous start time, or the property is a named finding

### Requirement: Flag equivalence is the single current engine
Travel-engine source MUST NOT read `TRAVEL_ENGINE_V2_ENABLED`. This change MUST NOT add that setting. The current selector, allocator, and validator MUST remain the only implementations, which is the pre-v8 output while no second engine exists.

#### Scenario: Engine does not branch on a V2 flag
- **WHEN** the travel-engine sources are scanned
- **THEN** none of them read `TRAVEL_ENGINE_V2_ENABLED`

### Requirement: Missing types stay skipped until their slice
Idempotent dedup MUST be skipped until a candidate normalizer exists. The skip reason MUST name slice 4.1. Area respect MUST be skipped until a search-area type exists. The skip reason MUST name slice 3. Neither skip MUST add that module or that type. A skip MUST still leave the suite exit code at 0.

#### Scenario: Dedup waits for the normalizer
- **WHEN** the property suite runs and no candidate normalizer module exists
- **THEN** idempotent dedup is skipped with a reason that names slice 4.1 and no normalizer module is created

#### Scenario: Area respect waits for search area
- **WHEN** the property suite runs and no search-area type exists
- **THEN** area respect is skipped with a reason that names slice 3 and no search-area type is created
