## Why

P5.14 live smoke (`scripts/test_agent.py` on Darjeeling) reaches WRAP_UP under NVIDIA NIM but fails section 4: `errors` from `trip_validator` and `abort_triggered=True` after max replan. Root cause is not Nominatim credentials or the LLM provider — `allocate_days` / `optimize_route` / morning schedule extract under-constrain days relative to the same rules the validator enforces (travel ≤180, morning-only ≤2 slots ≤10:30, geo stddev ≤15km). Without packing alignment, P5 cannot stamp green and P6 stays gated.

## What Changes

- Align day packing with validator: **morning-only ≤2 per day** in `allocate_days` (using `MORNING_ONLY_CATEGORIES`).
- Soft geo packing (**option A**): keep cluster preference / spill allowed; prefer not mixing far POIs onto a day when a better underfilled day exists — **do not** hard-reject adds solely on projected geo-coherence stddev.
- Route optimizer: return **full pairwise matrix** `legs` (not consecutive-only) so schedule morning-reorder can look up any hop; continue drop-retry until travel ≤ `MAX_DAILY_TRAVEL_MIN` or one stop remains (adjust `MAX_ROUTE_DROP_ATTEMPTS` if needed so a full day can thin to one stop).
- Schedule builder: when >2 morning-only stops are present, keep at most two in earliest slots and **do not** place excess morning-only ahead of non-morning stops in a way that guarantees slot-3+ morning validation failures (omit excess from the timed day or leave them after non-morning only if allocator already capped — prefer allocator as source of truth).
- Unit tests for the failure modes observed on Darjeeling (morning overflow, over-budget after 3 drops, morning extract + consecutive legs).
- After green deterministic packing + pytest: re-run P5.14 smoke (existing NIM/`LLM_*` env) — context.md stamp remains owned by `ship-p5-14-smoke-nvidia-nim` (or follow-up apply), not claimed here unless smoke is explicitly in tasks.

## Capabilities

### New Capabilities

- _(none)_ — this change tightens existing P4 travel-engine contracts rather than adding a new product surface.

### Modified Capabilities

- `travel-engine-day-allocator`: morning-only per-day cap; soft geo spill preference (A)
- `travel-engine-route-optimizer`: full-matrix `legs`; drop until under travel cap or one stop
- `travel-engine-schedule-builder`: morning extract must not leave excess morning-only in invalid mid slots when >2 arrive
- `travel-engine-rules`: `MAX_ROUTE_DROP_ATTEMPTS` may increase so a max-size day can thin to one stop under budget
- `planner-agent-smoke`: clarify that live section 4 green depends on packing producing validator-passing itineraries (no smoke softening; no rule relaxation)

## Impact

- **Code:** `src/travel_engine/day_allocator.py`, `route_optimizer.py`, `schedule_builder.py`, possibly `travel_rules.py`; tests under `tests/travel_engine/`
- **Already started:** full-matrix `legs` may already be present locally from the P5.14 apply spike — formalize + test in this change
- **AGENT.md:** `travel_engine/` stays pure (no LLM/network/DB); constants only via `travel_rules.py`
- **Blueprint:** drop-attempt ceiling may diverge from literal “max 3” if raised — document in design; prefer efficiency + validator alignment over leaving knowingly-invalid days
- **Non-goals:** relax `GEO_COHERENCE_MAX_STDDEV_KM` / `MAX_DAILY_TRAVEL_MIN` / morning latest; soften smoke §4; Nominatim/API keys; LLM client changes; P6 HTTP `/planner/generate`
- **Deferred todos (explicit):** (1) revisit geo/travel caps for mountain destinations after packing is coherent; (2) smoke policy for `accept_partial` only if packing still cannot green Darjeeling
- **Downstream:** Unblocks finishing `ship-p5-14-smoke-nvidia-nim` apply (smoke §4) without weakening ship criteria
