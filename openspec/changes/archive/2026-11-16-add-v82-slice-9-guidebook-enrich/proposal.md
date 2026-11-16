## Why

v8.2 defers accommodation and image providers, so a finished deterministic itinerary still cannot show a stay or a credited photo. Those two guidebook pieces were agreed as a later slice: deterministic, after the trip is saved, attached to canonical place IDs. The target plan has to say that before anyone implements it, or the next session will either skip them or bolt them onto the generate stream.

## What Changes

- Amend `docs/steps/wandr_blueprint_version8.md` in place. Heading becomes v8.3, an amendment of v8.2. The file path stays the same. v6.1 (`docs/blueprint_final.md`) and v7 (`docs/v2_blueprint.md`) stay the source of truth for what already shipped.
- Add **Slice 9 — Guidebook enrich** after Slice 6, allowed in parallel with Slice 7. Subslices 9.1–9.6 cover lodging ingest, suggested stays, optional confirmed stay as trip base, a `src/geo/media/` facade, additive media reads, and the frontend Stay block plus credited stop photos.
- Record the new contracts (`LodgingSuggestion`, `PlaceMedia`), flags (`LODGING_V1_ENABLED`, `MEDIA_ENRICH_ENABLED`, both default off), invariants, eval honesty checks, one guardrail, ADRs 015 and 016, and two definition-of-done lines.
- Remove "accommodation and image providers" from §16. Leave booking, referral links, live price, availability, generate-path image HTTP, unlabeled stock photos on a stop, and Google Places deferred.
- Slice 0.1's audit list gains today's display-only `accommodation_label`, gradient stop cards, and the "Stays are unavailable" copy.

This change edits that plan document only. It does not implement Slice 9.

## Capabilities

### New Capabilities

(none — plan-document amendment; no runtime behavior)

### Modified Capabilities

(none — no spec-level behavior changes; `.openspec.yaml` sets `skip_specs: true`)

## Impact

- **Files changed:** `docs/steps/wandr_blueprint_version8.md` only.
- **No impact on:** product code, tests, migrations, dependencies, API surface, SSE, or `docs/context.md` implemented-module status. Lodging ingest, place media, and the Stay block do not exist yet. `accommodation_label` on generate is display-only. The trip page Stay section is the static line "Stays are unavailable." `Place` has no media field.
- **Downstream:** a later guideagent change implements 9.1–9.5; a later frontend change implements 9.6. Both stay behind the flags this amendment defines. The parent planning change `free-media-map-guidebook` stays the cross-boundary note for providers and the guidebook layout; this amendment is the v8 sequence those notes plug into. It does not copy that vault doc into the blueprint.

## Non-goals

- No application code, tests, migrations, settings, or frontend edits in this change.
- No implementation of Slices 0–8.
- No hotel agent, photo agent, or growth of Slice 7.
- No booking inventory, affiliate or referral URLs, live prices, availability, or a model choosing a hotel.
- No image HTTP inside `POST /planner/generate`, and no raising of the 45-second ceiling.
- No MapTiler satellite or outdoor style toggle (frontend-only; stays in the parent media plan).
- No new mandatory API key.
- No claim that Slice 9 has shipped in `docs/context.md`.

## Constraints this amendment must keep

From `AGENT.md` / the v8.2 invariants, the new slice text must say:

- Lodging and media HTTP live under `src/geo/`. `travel_engine/` stays free of network, DB, and LLM I/O.
- LLM calls stay on `src/core/llm/client.py`. Slice 9 adds no model role.
- New reads use `ApiResponse[T]`. Existing paths, DTO shapes, and SSE event names stay byte-compatible.
- Env access stays on `get_settings()`. Flags default off.
- Unknown price and availability stay unknown. A photo without attribution is not shown.
- The plan must not invent an endpoint or setting as already present. Slice 0 verifies names before any later implementation adds them.

No conflict with `AGENT.md`. Nothing in this amendment asks a coding agent to break a locked contract.
