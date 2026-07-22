## 1. Promote hardened P2 prompts

- [x] 1.1 Copy `docs/steps/suggestedp2.md` contents over `docs/steps/step2.md` (full replace)
- [x] 1.2 Verify `step2.md` header includes “v2 — hardened” and the v2 Fix Log table
- [x] 1.3 Verify canonical build order appears once:
      `2.1 → 2.2 → 2.3 → 2.6a → 2.6b → 2.4 → 2.5 → 2.6c → 2.6c′ → 2.7a → 2.7b → 2.8 → 2.9 → 2.10`
- [x] 1.4 Spot-check locked decisions present: async dict cache (no lru_cache), geography cast, atomic upserts, mandatory dest check, 2.6c′ rate limit, seed partial-failure test

## 2. Remove duplicate draft

- [x] 2.1 Delete `docs/steps/suggestedp2.md` so agents have one source of truth

## 3. Context pointer (docs only)

- [x] 3.1 Update `docs/context.md` Current state / Next step note: P2 prompts finalized in `docs/steps/step2.md` (v2); next implement step remains P2.1 — do not mark geo modules as implemented

## 4. Sanity check

- [x] 4.1 Confirm no `lru_cache` instruction remains in `docs/steps/step2.md` for `geocode`
- [x] 4.2 Confirm readiness P2 acceptance still documents `tier=limited` (not blueprint’s premature `ready`)
