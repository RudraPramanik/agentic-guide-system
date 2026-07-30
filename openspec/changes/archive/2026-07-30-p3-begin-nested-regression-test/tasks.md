## 1. Real-session SAVEPOINT regression

- [x] 1.1 In `tests/scripts/test_p3_scripts.py`, add an async test that seeds one destination + three places via real `db_session` (follow existing places/destination test fixtures)
- [x] 1.2 Patch `PlaceService._call_llm_and_parse` to return valid `ParsedEnrichment` for all three places (no live LLM)
- [x] 1.3 Patch the write path used inside `enrich_places` so the second `update` raises; leave calls 1 and 3 succeeding
- [x] 1.4 Call `enrich_places(db_session, destination_id, ...)`, assert success count `2`, places 1 and 3 have summary/`enriched_tags`, place 2 unchanged
- [x] 1.5 Run `python -m pytest tests/scripts/test_p3_scripts.py -v` and confirm the new test fails if `begin_nested` is removed (optional smoke by temporarily commenting SAVEPOINT locally — do not commit that)

## 2. Close-out

- [x] 2.1 Keep existing mock tests for parse-None continue and `limit=0` intact
- [x] 2.2 No `docs/context.md` bump required unless production code changes (test-only change)
