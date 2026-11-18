---
id: '0542'
title: SpiceDB Live Schema Harness and Strict Name Contract
status: Complete
created: 2026-11-17
dependencies:
- TASK-0540
- TASK-0541
governing_adrs:
- ADR-0001
- ADR-0014
governing_prds: []
governing_stories:
- US-0013
target_release: 0.9.0
---

# TASK-0542: SpiceDB Live Schema Harness and Strict Name Contract

## Status
Complete

## Summary
The test suite passes while production calls fail. `MockSpiceDBClient` accepts undefined relations and permissions. It maps `play`, `read`, and `control` to other names. It treats role names such as `dungeon_master` and `gm` as grants. Some authorization tests run only against this mock. This task makes the mock reject any name that the schema does not define, the way SpiceDB does. It removes the role-name fallbacks. It adds a live SpiceDB test path that loads the real schema, and it adds one name-contract module that every other task uses.

## Problem Statement
- `libs/runefoble_auth/src/runefoble_auth/mock/evaluator.py:22-29` (`ALIAS_MAP`) maps `read`, `inspect`, `observe`, `control`, `participate`, and `move_token` to schema names. Real SpiceDB rejects these names.
- `mock/evaluator.py:10-18` (`DM_PERMS`, `PLAYER_PERMS`, `SPECTATOR_PERMS`) and `:84-94` grant campaign access to the relations `dungeon_master`, `game_master`, and `gm` (`w3-authz-coverage.md` F17).
- The mock accepts writes to undefined relations. Examples: `campaign#gm`, `codex_entry#party_shared`, `campaign#viewer` (`w2-campaign-lore.md` F21).
- More than 20 blackbox tests write `campaign#play`, `campaign#view`, and `campaign#run_session` as tuples. Those are permissions, not relations (`tests/test_blackbox_campaign_atlas_and_codex.py:108-110`, `tests/test_blackbox_campaign_lore_rag.py:175-182`).
- `tests/helpers/spicedb.py` starts a real container but does not load the schema. Its tests skip when Docker is missing, so CI can pass with no live check.

## Documentation & Architecture Review
- ADR-0014 requires blackbox setup through frontdoors. Tuples written directly into a test store are a backdoor. Live tests must set up grants through public routes, or through the library write path for libs-only tests.
- `docs/how-to/define-spicedb-zanzibar-permissions.md` must describe the name contract and the live test command.
- The Makefile `test` target must not change its default behaviour. A new target runs the live authorization suite.

## Product & User Story References
- US-0013 (gateway Zanzibar authorization). ADR-0014 for test shape.

## Detailed Specification & Implementation Plan
1. `libs/runefoble_auth/src/runefoble_auth/contract.py`:
   - `load_contract()` parses `runefoble.zed` once with `parse_zed_schema`.
   - `require_permission(resource_type, name)` and `require_relation(resource_type, name)` raise `SchemaContractError` when the name is not defined.
   - `ACTION_PERMISSIONS`: one mapping from a domain action to a `(type, permission)` pair. Every bounded-context task uses these constants. Include at least: `campaign.manage`, `campaign.run_session`, `campaign.play`, `campaign.view`, `session.control`, `session.participate`, `session.observe`, `character.edit`, `character.view`, `character.delete`, `board.manage_traps`, `board.view_secret_layer`, `board.switch_map`, `board_token.move`, `codex_entry.view`, `codex_entry.edit`, `atlas.edit`, `atlas.place_pin`, `lore_document.read_secret`, `homebrew_rule.manage`, `audience_poll.vote`, `audience_poll.approve`, `audience_poll.view`.
2. Strict mock: `MockSpiceDBClient` (`mock/client.py`, `mock/evaluator.py`):
   - Reject writes to an undefined type, relation, or subject. Raise `SchemaContractError`.
   - Reject checks against an undefined permission. Raise `SchemaContractError`.
   - Delete `ALIAS_MAP`, `DM_PERMS`, `PLAYER_PERMS`, `SPECTATOR_PERMS`, `FALLBACK_RES`, and every role-name branch. Evaluate only schema-defined permissions through the schema graph.
   - Keep the arrow and union evaluation. Keep caveats if present.
3. Live harness: in `tests/helpers/spicedb.py` add a module-scoped fixture `live_spicedb_with_schema`:
   - Start the container with the image tag from `deployments/helm/runefoble/values.yaml` (`spicedb.image`). Use the same tag in the test helper.
   - Apply `runefoble.zed` with `bootstrap_schema`. A failed write means the schema is invalid, so the fixture fails.
   - When `RUNEFOBLE_REQUIRE_LIVE_SPICEDB=1`, a missing Docker or a failed start raises. It does not skip.
   - Yield the endpoint and a client built with the test preshared key.
4. Add the Make target `test-authz-live` that sets `RUNEFOBLE_REQUIRE_LIVE_SPICEDB=1` and runs `uv run pytest -m authz_live`. Register the marker in `pyproject.toml` (root).
5. Test migration: every test that the strict mock rejects is changed in this task when it sits in `tests/helpers/` or `tests/conftest.py`. Tests in a single bounded context are migrated by that context's task (listed in the index). If the migration in this task would exceed about 15 files, move the affected tests to the owning task and say so in the index report.
6. Write `libs/runefoble_auth/tests/test_contract_names.py`:
   - Every `ACTION_PERMISSIONS` entry resolves in the parsed schema.
   - The strict mock rejects `campaign#play` as a relation write and `campaign#gm` as a relation write.
   - The strict mock accepts `campaign#owner` and `campaign#game_master` writes.

## Frontdoor Blackbox Test Plan
- `tests/test_authz_live_contract.py` (marker `authz_live`) uses `live_spicedb_with_schema`:
  - Writing `campaign:c1#play@user:u1` is rejected by SpiceDB. The test asserts `AuthzSchemaError`.
  - Writing `campaign:c1#game_master@user:u1` succeeds. A check for `campaign:c1#run_session` for `u1` returns allowed.
  - A check for an undefined permission raises `AuthzSchemaError`.
- Before this task the live suite does not exist. After this task it passes with Docker running, and it fails (not skips) when `RUNEFOBLE_REQUIRE_LIVE_SPICEDB=1` and Docker is absent.

## Definition of Done
1. `contract.py`, the strict mock changes, and the live fixture exist.
2. `make test-authz-live` passes with Docker. It fails with a clear message when Docker is absent.
3. `uv run pytest libs/runefoble_auth` passes.
4. `uv run pytest` passes for every test file this task migrated. The index report lists the files that the owning bounded-context tasks must migrate.
5. No test in `tests/helpers/` or `tests/conftest.py` writes a permission name as a relation.
6. `docs/how-to/define-spicedb-zanzibar-permissions.md` documents the name contract and the live command.
7. No file in the change exceeds 500 lines.

## Orchestrator Addenda (2026-11-17, round 2)

Source: `.audit/synth/discovered-round2.md`.

- grpc_lookup_resources in libs/runefoble_auth has no live SpiceDB test. Only the mock path is covered. Add a live case to the live schema harness.

## Audit Provenance

- Severity: high
- Source audits: `w3-authz-coverage.md`, `w2-campaign-lore.md`, `w2-audience-studio.md`
