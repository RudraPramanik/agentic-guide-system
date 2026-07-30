## 1. Banner & versioning

- [ ] 1.1 Update `docs/blueprint_final.md` title/subtitle to **v6.1 (P4 pre-flight merge)** and note it supersedes the standalone addendum in `docs/blueprint.md`
- [ ] 1.2 Add a “What's in this version” row summarizing the pre-flight merge (vocabulary fix, CORS/SameSite, route locks, P5/P6 D.* locks)

## 2. Travel engine design sections

- [ ] 2.1 Replace `travel_rules.py` code block with corrected structural vs interest vocabulary from `docs/blueprint.md` §B (incl. `VISIT_DURATION_DEFAULT_MIN`, no `sunrise_point`)
- [ ] 2.2 Update `place_selector.py` bullets: sum scoring formula; `explain_selection` → tool_trace (not new TripEvaluation column)
- [ ] 2.3 Update `day_allocator` / `schedule_builder` bullets: duration via `.get(category, VISIT_DURATION_DEFAULT_MIN)`; wall-clock naive times note
- [ ] 2.4 Update `route_optimizer.py`: brute-force permutations; drop-retry ≤3; required `dropped_stops` field; no TSP package

## 3. Agent / tools / evaluation locks

- [ ] 3.1 Update ToolContext + TravelState notes: non-serializable `db`/`routing` stay out of LangGraph state (D.1); preferred session-per-DB-tool (D.2)
- [ ] 3.2 Expand Deterministic Fallback / agent node notes with nudge + one `tool_choice=required` retry then default tool (D.9)
- [ ] 3.3 Clarify evaluation: selection explanations land in `tool_trace`, not a new column (D.8)

## 4. Environment, CORS, install order

- [ ] 4.1 Add `CORS_ALLOWED_ORIGINS` and `PLANNER_ABSOLUTE_MIN_PLACES` to Environment Variables (and any settings table)
- [ ] 4.2 Document CORSMiddleware + SameSite Option A (MVP) in a short Deployment / cross-cutting section
- [ ] 4.3 Fix Package Install Order: pytest packages at step 1.11; adjust or annotate the old 7.3 row

## 5. Phase step bullets (P4–P6)

- [ ] 5.1 P4: add step **4.0 CORS**; amend 4.2–4.7 bullets for vocabulary, scoring, permutation TSP, `dropped_stops`, `.get()` durations
- [ ] 5.2 P5: amend 5.6 / 5.9 (and tool notes as needed) for ToolContext-out-of-state, session preference, agent nudge mechanics; REPLAN guidance when `dropped_stops` already present
- [ ] 5.3 P6: rewrite 6.2 SSE to queue + background task + disconnect cancel + absolute min places pre-check; fix 6.4 cache key; lock guest ownership in 6.1/6.3
- [ ] 5.4 Add brief deferred Production hardening notes (Section E) labeled non-blocking

## 6. Demote addendum & align dependents

- [ ] 6.1 Replace `docs/blueprint.md` body with a short pointer: merged into `blueprint_final.md` v6.1; not a competing SoT
- [ ] 6.2 Update `docs/context.md` with one-line SoT pointer to `blueprint_final.md` v6.1 (and SameSite Option A if not already)
- [ ] 6.3 Update `openspec/changes/p4-travel-engine/proposal.md` (and design conflict note if present) so blueprint_final v6.1 is cited as SoT, not “follow addendum over master”
- [ ] 6.4 Grep proof: `blueprint_final.md` has no `sunrise_point` in rules; duration map includes `attraction`/`trailhead`; cache key mentions `base_lat`/`base_lng`; `blueprint.md` is pointer-only
