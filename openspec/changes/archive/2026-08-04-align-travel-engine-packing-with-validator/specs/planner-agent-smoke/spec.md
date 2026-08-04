## ADDED Requirements

### Requirement: Live smoke section 4 depends on packing producing valid itineraries
Live `scripts/test_agent.py` section 4 (`errors==[]`, `abort_triggered==False`) MUST remain strict. Operators MUST NOT soften section 4 or treat `abort_triggered=True` as PASS to ship P5. When smoke fails validation on Darjeeling after a working LiteLLM provider is configured, the fix MUST be travel-engine packing / replan quality — not Nominatim credentials (Nominatim is unused at smoke time when the destination is already seeded) and not relaxing `GEO_COHERENCE_MAX_STDDEV_KM` / `MAX_DAILY_TRAVEL_MIN` / morning-slot rules in the same change unless explicitly agreed as a separate deferred product decision.

#### Scenario: Validation failures are packing issues not geocoder keys
- **WHEN** smoke fails section 4 with travel-cap, morning-slot, or geo-coherence errors while Darjeeling is seeded+enriched+indexed and LLM tools succeed
- **THEN** the failure MUST be treated as a travel_engine / itinerary quality defect, not as a missing Nominatim API key

#### Scenario: Smoke criteria stay strict
- **WHEN** packing changes are applied and smoke is re-run
- **THEN** section 4 still requires empty hard `errors` and `abort_triggered==False` for overall PASS
