# ADR-001 — Modular monolith

## Context

Blueprint v8.3 §21 names this decision: v8.2 stays a modular monolith. §5.3 adds packages inside the existing process (`location_intelligence/`, `planner/runs/`, `geo/media/`). §16 lists microservices as deferred until there is measured demand, an ADR, and a golden-suite extension. The repository audit found those packages absent. This record does not create them.

## Decision

v8.3 stays one process. New work lands in the existing package layout. Microservices stay deferred.

## Alternatives

Split the planner, travel engine, and geo gateways into separate services. Rejected. §16 already defers that split, and Slice 0 has no measurement that would justify it.

## Consequences

This record does not create a service, a deployable, or a new package. Later slices add code inside this process: run tracking in Slice 1 (`planner/runs/`), location resolution in Slice 3 (`location_intelligence/`), lodging and media in Slice 9. None of those slices start from this file.

## Migration and rollback

No migration and no deploy. Rollback is deleting this file.

## Status

accepted
