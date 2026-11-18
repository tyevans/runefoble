---
id: '0540'
title: SpiceDB Schema Corrections and Missing Relations
status: Complete
created: 2026-11-17
dependencies: []
governing_adrs:
- ADR-0001
- ADR-0007
governing_prds:
- PRD-0007
- PRD-0018
governing_stories:
- US-0009
- US-0013
- US-0050
target_release: 0.9.0
---

# TASK-0540: SpiceDB Schema Corrections and Missing Relations

## Status
Complete

## Summary
`libs/runefoble_auth/schema/runefoble.zed` is the only authority for object permissions (AGENTS.md Hard Invariant 1). Code writes and checks names that the schema does not define. Some names are missing, and one object type is used but never defined. This task fixes the schema itself. It adds the missing permission and relations that the rest of the theme depends on. It does not change any call site. Call sites move in the owning bounded-context tasks.

## Problem Statement
- `character` has no `delete` permission. `gateway/api/src/gateway_api/routers/characters.py:118` checks `require_zanzibar_permission("owner", "character", ...)`, and `owner` is a relation, not a permission (`w3-authz-coverage.md` F16).
- `codex_entry` has no `party_shared` or `public` relation. `services/campaign_lore/src/campaign_lore/codex_deps.py:83-93` writes `codex_entry#party_shared@campaign:<id>` and `codex_entry#public@campaign:<id>`. Live SpiceDB rejects these writes, so a shared entry is saved with no ACL (`w2-campaign-lore.md` F8).
- `system` is written by `gateway/api/src/gateway_api/routers/auth/admin.py:18`. No `definition system` exists. The write is wrapped in `suppress(Exception)` (`w1-libs.md` F5). TASK-0544 removes the routes. This task records that no `system` type is added.
- `campaign#viewer` is written by `gateway/api/src/gateway_api/routers/auth/registration.py:22`. `campaign` has no `viewer` relation (`w1-libs.md` F5). TASK-0543 removes the write.
- `game_session` and `session` are both defined. Only `session` has a writer (`gateway/api/src/gateway_api/routers/campaigns.py:55`). Services check `game_session` and never write it (`w1-game-session.md` F7, F8). This task records the decision that `session` is the lifecycle object. `game_session` stays in the file until TASK-0559 removes it.

## Documentation & Architecture Review
- `docs/how-to/define-spicedb-zanzibar-permissions.md` lists the schema relations. It must match the file after this change.
- `docs/explanation/zanzibar-in-ttrpg.md` gives the design intent for codex privacy. Update it if the codex relation model changes.
- ADR-0001 requires object checks against `runefoble.zed`. ADR-0007 requires that each bounded context owns its object type.
- No new bounded context is created. No new object type is created.

## Product & User Story References
- PRD-0007 (campaign lore, codex privacy levels `private`, `party_shared`, `public`).
- PRD-0018 (West Marches shared world, `shared_world` and `caravan_contract` checks).
- US-0050 (collaborative atlas and living codex, privacy levels).
- US-0009 and US-0013 (campaign access control at the gateway).

## Detailed Specification & Implementation Plan
1. Edit `libs/runefoble_auth/schema/runefoble.zed`:
   - `definition character`: add `permission delete = owner`. Keep `edit` and `view` unchanged.
   - `definition codex_entry`: add `relation party_shared: campaign` and `relation public: campaign`. Change `view` to `author + editor + reader + party_shared->play + public->view`. Keep `edit` and `manage` unchanged.
   - Do not add `definition system`. Do not add `campaign#viewer`. Do not add `session` permissions. Do not remove `game_session` in this task.
2. Add a short comment above each changed definition. The comment states the intent in one line.
3. Add a unit test file `libs/runefoble_auth/tests/test_schema_contract_relations.py`:
   - Parse the schema with `runefoble_auth.mock.schema_parser.parse_zed_schema`.
   - Assert that `character` has `delete`, and that `codex_entry` has `party_shared` and `public` relations.
   - Assert that `system` and `campaign.viewer` are not defined.
4. Update `docs/how-to/define-spicedb-zanzibar-permissions.md` and `docs/reference/` (if it lists schema names) to match the new schema. Fix any statement that conflicts with the file.
5. Do not edit call sites. Each call site moves in its owning task (listed in the index report).

## Frontdoor Blackbox Test Plan
- This task has no HTTP behaviour of its own. Its acceptance test is the schema parse test in step 3.
- The schema is validated by SpiceDB itself when it is written. TASK-0542 adds a live test that writes `runefoble.zed` to a real SpiceDB container. That test must pass after this change. Before this change it fails on the codex relation check (`codex_entry` owner write through a public frontdoor is added by TASK-0553).

## Definition of Done
1. `runefoble.zed` contains the additions in step 1 and no other permission or relation change.
2. `uv run pytest libs/runefoble_auth/tests/test_schema_contract_relations.py` passes.
3. `docs/how-to/define-spicedb-zanzibar-permissions.md` matches the schema.
4. No Python or TypeScript call site is changed in this task.
5. `uv run ruff check libs/runefoble_auth` passes.
6. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w3-authz-coverage.md`, `w2-campaign-lore.md`, `w1-libs.md`, `w1-gateway-api.md`
