## 1. Remove parallel critics doc

- [x] 1.1 Delete `docs/step7_critics.md`
- [x] 1.2 Edit `docs/steps/step7.md` header: remove the “Historical review notes → step7_critics” lines; keep OpenSpec / v2.1 attribution and locks unchanged

## 2. Spec + verify

- [x] 2.1 Apply delta to `openspec/specs/p7-step7-build-contract/spec.md` (sole SoT; no parallel critics file; drop “choose between” scenario)
- [x] 2.2 Grep live tree for `step7_critics` excluding `openspec/changes/archive/` — expect no remaining active refs under `docs/` or `openspec/specs/`
- [x] 2.3 Do **not** bump P7 Progress in `docs/context.md` (docs hygiene only; 7.0 already ✅)
