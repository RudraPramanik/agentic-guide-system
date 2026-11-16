## ADDED Requirements

### Requirement: Post-P7 blueprint is not pasted into the v6 master

`docs/blueprint_final.md` MUST remain the P0–P7 planner master and MUST end at that v6.1 contract. It MUST NOT also contain the v7 phase body (V0–V6). Post-P7 build steps MUST live only in `docs/v2_blueprint.md`. `docs/blueprint_final.md` MAY end with a short pointer to `docs/v2_blueprint.md`. The two files MUST NOT carry duplicate full copies of the v7 blueprint.

#### Scenario: Reader finishes the P0–P7 master

- **WHEN** a reader reaches the end of `docs/blueprint_final.md`
- **THEN** they do not find a second copy of the v7 blueprint, and a pointer tells them post-P7 steps are in `docs/v2_blueprint.md`

#### Scenario: Reader needs a v7 step

- **WHEN** a reader looks up V0–V6 build steps
- **THEN** the only full copy is `docs/v2_blueprint.md`
