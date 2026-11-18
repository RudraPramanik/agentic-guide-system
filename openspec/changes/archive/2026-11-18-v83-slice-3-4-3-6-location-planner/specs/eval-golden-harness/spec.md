## ADDED Requirements

### Requirement: The location suite does not enter the itinerary loader
`python scripts/run_evals.py --replay --suite location` MUST score only `evals/golden/location/*.json` and MUST exit 0 when those cases meet the location gates. It MUST NOT call `PlannerService`, an LLM, the network, or a database. `--replay` on that suite MUST NOT read provider fixtures and MUST NOT change the score.

The default command without `--suite` MUST keep loading `evals/golden/darjeeling` only. The twelve Darjeeling files MUST stay `itinerary_preference`. The closed itinerary assertion set MUST NOT gain keys for this suite. Location files MUST NOT be passed through that assertion loader.

The suite MUST report location-type accuracy of at least 0.95, MUST show that every ambiguous case asks for confirmation and does not select a candidate, and MUST show search-area containment of at least 0.98. A labeled stop outside the area MUST be excluded. The fixtures MUST cover a city (`Darjeeling`), a landmark (`Tiger Hill`), an ambiguous pair, a map pin whose radius clamps at `LOCATION_MAX_RADIUS_KM`, and one stop outside a radius.

#### Scenario: The location command does not generate a trip
- **WHEN** `python scripts/run_evals.py --replay --suite location` runs
- **THEN** it exits 0, does not call the planner, and does not score the Darjeeling itinerary files

#### Scenario: The default replay command ignores the location folder
- **WHEN** `python scripts/run_evals.py --replay` runs with no `--suite`
- **THEN** it loads the Darjeeling itinerary cases and does not load `evals/golden/location`

#### Scenario: An outside stop fails containment
- **WHEN** a location case marks a stop outside the area and the filter keeps that stop
- **THEN** the suite exits non-zero
