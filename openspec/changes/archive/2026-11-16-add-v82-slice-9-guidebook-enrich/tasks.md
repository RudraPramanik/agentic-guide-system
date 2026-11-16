## 1. Read before editing

- [x] 1.1 Re-read `docs/steps/wandr_blueprint_version8.md` (§1, §4, §5, §6, §7, §8, §9 order and Slice 0.1, §10, §11, §13, §15, §16, §20, §21) and this change's `design.md`. Edit only `docs/steps/wandr_blueprint_version8.md`.

## 2. Title, outcomes, and flow

- [x] 2.1 Retitle the document v8.3, an amendment of v8.2. State that v6.1 and v7 remain the source of truth for shipped work. Update the one-line summary so Slice 9 is post-save guidebook enrich, not an agent layer.
- [x] 2.2 Add two §1 outcome rows for suggested stays and credited photos, both sourced from Slice 9.
- [x] 2.3 In §5.1, add the post-persistence branch: lodging search inside the search area, and media resolve per stop. Both are flag-gated and outside the planner graph.
- [x] 2.4 In §5.2, list lodging retrieval and media resolution as deterministic services. In §5.3, add `src/geo/media/` only. Lodging stays on the existing geo and places pipeline.

## 3. Contracts, flags, and data

- [x] 3.1 Add `LodgingSuggestion` and `PlaceMedia` under §6 as proposed contracts. A suggestion carries `place_id`, name, coordinates, category, distance to the trip base, and `price_status` / `availability_status` of `unknown`. Media carries `url`, `source` (`osm`, `wikimedia`, or `opentripmap`), `attribution`, and `fetched_at`. No price field, booking URL, or rating.
- [x] 3.2 Add `LODGING_V1_ENABLED` and `MEDIA_ENRICH_ENABLED` to the §7 flag matrix, both default `false`, with the off behavior from design decision 6. Mention proposed `MEDIA_SOURCES` and `WIKIMEDIA_USER_AGENT` as add-only-when-used. No new mandatory key. Do not raise the generate timeout.
- [x] 3.3 In §8.1, add additive `places.media` JSONB only. State lodging rows are places with `category=lodging`, not a new table. In §8.5, point lodging at cost label `unknown`.

## 4. Slice 9

- [x] 4.1 Update the locked order diagram: Slice 9 after Slice 6, beside Slice 7, and not gated on the Slice 7 ship decision. Entry requires 6.2 (canonical `place_id`, suggested versus routed).
- [x] 4.2 Add the Slice 9 subslice table (9.1–9.6) in the same columns as the other slices: lodging ingest, suggested stays, optional confirmed stay as trip base, media facade and cache, additive media GETs, frontend Stay block and credited stop photos. Each row has allowed paths, tests, verify, rollback (flag off), and a stop condition. Mark endpoints and settings as proposed. 9.6 halts for release without a named frontend owner. Add one pointer to `docs/context/free-media-map-guidebook.md` and do not paste that catalog.
- [x] 4.3 Extend the Slice 0.1 audit row so it records display-only `accommodation_label`, gradient stop cards, and the "Stays are unavailable" copy.

## 5. Rules, gates, and deferred work

- [x] 5.1 Add invariants N11–N15: no lodging or media HTTP on generate; a suggestion is not a stop; price and availability stay unknown; a photo without attribution is not shown; a stop with no photo keeps the non-photo fallback.
- [x] 5.2 Add the §10 guardrail that `planner/service.py` and `travel_engine/` do not import the lodging client or `src/geo/media/`.
- [x] 5.3 Add §11 honesty checks as inform-only: no invented price, every suggestion has a `place_id`, out-of-area suggestions are absent or disclosed, attribution accompanies every URL, and low photo coverage is a pass. Flag-off generate replay stays byte-identical.
- [x] 5.4 In §13, list the two media GETs as additive and proposed, and name the Stay block plus visible photo credit as the frontend contract.
- [x] 5.5 In §15, state that image URLs are untrusted, Wikimedia calls send the configured user-agent, and a media proxy uses the existing SSRF rules.
- [x] 5.6 Remove "accommodation and image providers" from §16. Keep booking, referral links, live price, availability, generate-path image HTTP, unlabeled stock photos on a stop, and Google Places deferred.
- [x] 5.7 Add the two Slice 9 lines to §20. Add ADR 015 and ADR 016 to §21.

## 6. Check the edit

- [x] 6.1 Re-read the amended file and confirm: v8.3 heading; Slice 9 after Slice 6; both flags default off; N11–N15 present; §16 no longer defers accommodation and image providers as a class; generate timeout still 45 seconds; no application code, test, migration, or `docs/context.md` change. This is a plan amendment, not a completed build step, so do not update `docs/context.md`.
