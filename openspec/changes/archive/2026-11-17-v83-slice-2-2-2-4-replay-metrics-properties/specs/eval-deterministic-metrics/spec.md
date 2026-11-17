## Purpose

Pure functions that measure location, retrieval, duplicates, coherence, feasibility, preference, persistence, and map consistency, with hand-computed results and no effect on the golden pass/fail verdict.

## ADDED Requirements

### Requirement: Metrics are pure and do not change the golden verdict
Each metric MUST be a pure function of its inputs. It MUST NOT call an LLM, the network, or a database, and it MUST NOT mutate inputs. The same inputs MUST return the same number twice. These functions MUST NOT add or remove golden assertion keys and MUST NOT change how an existing golden case passes or fails.

#### Scenario: Repeated call matches
- **WHEN** a metric is called twice with the same inputs
- **THEN** both results are equal

#### Scenario: Golden verdict is unchanged
- **WHEN** an existing Darjeeling case is scored before and after the metrics module exists
- **THEN** the pass/fail verdict and the reasons for that case stay the same

### Requirement: Location accuracy is the labeled match rate
Location accuracy MUST be the number of predicted types that equal the labeled type, divided by the number of labeled items. Comparison MUST be exact on the type string. An empty labeled list MUST return `1.0`.

#### Scenario: Two of three types match
- **WHEN** the labeled types are city, landmark, and poi, and the predicted types are city, landmark, and city
- **THEN** the accuracy is `2/3`

#### Scenario: Empty location labels
- **WHEN** the labeled list is empty
- **THEN** the accuracy is `1.0`

### Requirement: Retrieval recall at k counts each label once
Recall at k MUST be the number of distinct labeled ids that appear in the first k retrieved ids, divided by the number of distinct labeled ids. An id repeated inside the first k MUST count once. An empty labeled set MUST return `1.0`.

#### Scenario: One of two labels is in the top ten
- **WHEN** the labeled ids are a and b, k is 10, and the retrieved ids start with a and then nine other ids that are not b
- **THEN** the recall is `0.5`

#### Scenario: Repeated hit still counts once
- **WHEN** the only labeled id is a, k is 10, and a appears twice inside those ten
- **THEN** the recall is `1.0`

### Requirement: Duplicate stops count extras beyond the first
The duplicate-stop metric MUST return how many stop occurrences are beyond the first occurrence of each place id. Ids a, a, b MUST return `1`. Ids a, a, a MUST return `2`. A list of unique ids MUST return `0`.

#### Scenario: One repeated id
- **WHEN** the stop ids are a, a, and b
- **THEN** the duplicate count is `1`

#### Scenario: Unique ids
- **WHEN** every stop id appears once
- **THEN** the duplicate count is `0`

### Requirement: Geographic coherence is the validator dispersion in kilometers
Geographic coherence MUST be the per-day coordinate dispersion in local kilometers already defined by the trip validator: offsets from the centroid, sample variance on the north and east axes, then the square root of the sum of those variances. Fewer than two coordinates MUST return no score. Two identical coordinates MUST return `0`. A lower number is tighter. Adding a coordinate that is farther from the current centroid than every existing coordinate MUST NOT decrease the score. This is the only coherence definition. A later property test MUST call this metric and MUST NOT use a second formula.

#### Scenario: One coordinate has no score
- **WHEN** a day has a single coordinate
- **THEN** the metric returns no score

#### Scenario: Identical coordinates score zero
- **WHEN** a day has two equal coordinates
- **THEN** the score is `0`

#### Scenario: A farther point does not tighten the day
- **WHEN** a day has two coordinates and a third coordinate is farther from their centroid than either existing point
- **THEN** the new score is greater than the score of the original two

### Requirement: Feasibility is the share of days inside the caps
Schedule feasibility MUST be the number of days that fit both the given active-time cap and the given travel cap, divided by the number of days. The caps MUST be arguments. An empty day list MUST return `1.0`. A day over either cap MUST count as not fitting.

#### Scenario: One of two days fits
- **WHEN** two days are scored, the first is within both caps, and the second exceeds the travel cap
- **THEN** feasibility is `0.5`

#### Scenario: Empty day list
- **WHEN** there are no days
- **THEN** feasibility is `1.0`

### Requirement: Preference is the share of places that match an interest
Preference MUST be the number of selected places whose category or tags intersect the interest list, divided by the number of selected places. Comparison MUST be case-insensitive. An empty selected list MUST return `1.0`. This metric MUST NOT call a judge.

#### Scenario: One of two places matches
- **WHEN** the interests are tea and the selected categories are tea and museum
- **THEN** the preference score is `0.5`

### Requirement: Persistence match is identity of id sequence
Persistence consistency MUST be a match only when each day's place-id sequence in the saved trip equals the generated sequence in the same order. Any missing id, extra id, or reorder MUST be a mismatch. The function MUST compare the two structures in memory and MUST NOT open a database.

#### Scenario: Same order matches
- **WHEN** the generated days and the saved days have the same place ids in the same order
- **THEN** the metric reports a match

#### Scenario: Reordered day mismatches
- **WHEN** one saved day lists the same ids in a different order
- **THEN** the metric reports a mismatch

### Requirement: Map consistency is feature order against stop order
Map consistency MUST be a match only when the GeoJSON feature ids, in order, equal the itinerary stop ids, in order. A missing feature, an extra feature, or a different order MUST be a mismatch. The function MUST NOT read a map tile or a database.

#### Scenario: Same ids in order match
- **WHEN** the feature ids are p1, p2 and the stop ids are p1, p2
- **THEN** the metric reports a match

#### Scenario: Extra feature mismatches
- **WHEN** the features include one id that is not a stop
- **THEN** the metric reports a mismatch
