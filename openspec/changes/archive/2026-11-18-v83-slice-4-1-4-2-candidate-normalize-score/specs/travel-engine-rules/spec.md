## ADDED Requirements

### Requirement: V2 normalizer and scoring constants live in travel_rules
`travel_rules.py` MUST define the constants used by the candidate normalizer and V2 scoring terms as data (not hardcoded inside call sites), including at least: proximity radius for name/alias dedup, minimum merge confidence, and numeric weights for diversity, geo fit, evidence, and duplicate penalty. Existing structural maps (`VISIT_DURATION_BY_CATEGORY`, `MORNING_ONLY_CATEGORIES`, `AVOID_SAME_DAY_PAIRS`) and interest `CATEGORY_WEIGHTS` MUST remain. The module MUST stay free of I/O and MUST NOT import geo, LLM, or DB clients. A weight value that changes ranking behavior MUST be backed by a golden preference or duplicate fixture before it is treated as shippable; otherwise the change MUST stop rather than invent a weight.

#### Scenario: V2 weights are named constants
- **WHEN** `travel_rules` is inspected for V2 scoring
- **THEN** diversity, geo fit, evidence, and duplicate-penalty weights exist as module-level constants

#### Scenario: Normalizer thresholds are named constants
- **WHEN** `travel_rules` is inspected for normalization
- **THEN** proximity and confidence thresholds exist as module-level constants
