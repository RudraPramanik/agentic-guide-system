## Why

`docs/step7_critics.md` is a parallel quasi-prompt beside the real P7 build contract. Agents can treat it as authoritative even though locks already live in `docs/steps/step7.md` v2.1. Remove it so each step has a single source of truth under `docs/steps/`.

## What Changes

- **Delete** `docs/step7_critics.md`.
- Trim `docs/steps/step7.md` header so it no longer links to the critics file as “historical review.”
- **MODIFIED** `p7-step7-build-contract`: drop wording that assumes the critics file exists; keep “step7.md is the only build contract.”
- **Non-goals:** P7 application code (7.1+); rewriting step7 locks; deleting OpenSpec archive history; changing blueprint.

## Capabilities

### New Capabilities
- *(none)*

### Modified Capabilities
- `p7-step7-build-contract`: Critics file no longer part of the docs surface; SoT remains `docs/steps/step7.md` alone.

## Impact

- **Docs:** delete critics file; small header edit on `step7.md`.
- **Specs:** `openspec/specs/p7-step7-build-contract/spec.md` updated on apply/archive sync.
- **Runtime/code:** none.
- **Recovery:** git history + `openspec/changes/archive/2026-08-06-harden-p7-step7-prompt/` retain critic-era design notes.
