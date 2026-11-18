---
id: '0555'
title: Rules Compendium Homebrew Read, Write, and Identity Authorization
status: Refined
created: 2026-11-17
dependencies:
- TASK-0520
- TASK-0541
- TASK-0542
- TASK-0540
- TASK-0625
- TASK-0527
governing_adrs:
- ADR-0001
- ADR-0007
- ADR-0014
governing_prds:
- PRD-0008
governing_stories:
- US-0052
- US-0037
target_release: 0.9.0
---

# TASK-0555: Rules Compendium Homebrew Read, Write, and Identity Authorization

## Status
Refined

## Summary
The rules compendium returns homebrew from a private campaign to anonymous callers, through both the list route and the search route. It writes homebrew rules for any identity from a raw header with no token check. Its helper returns success when identity is missing. This task makes homebrew reads and writes depend on a schema permission, uses the verified principal, and returns only SRD content to callers with no campaign grant.

## Problem Statement
- `services/rules_compendium/src/rules_compendium/dependencies.py` (`check_user_can_view_campaign`): returns True when `user_id` is falsy. This feeds `routers/homebrew.py` (list) and `routers/rules.py` (search with `campaign_id`). Probe: an anonymous list returned two homebrew rules, and an anonymous search returned homebrew hits (`w2-rules-compendium.md` F1).
- `dependencies.py` `get_current_user_id` reads `x-user-id` with no token check. Probe: `POST /api/v1/compendium/homebrew` with `x-user-id: dm1` and no credential returned 200 and wrote a rule as `dm1` (`w2-rules-compendium.md` F2).
- `dependencies.py:51` reads a setting that does not exist (`w2-rules-compendium.md` F3). TASK-0625 fixes the setting. TASK-0541 replaces the factory.
- `routers/homebrew.py:26` (`POST /api/v1/compendium/homebrew`) uses `check_user_can_manage_homebrew`, which fails closed on a missing identity. Its permission names are checked against the schema only after TASK-0540 and this task. Confirm the names used are `homebrew_rule.manage` and `campaign.manage`.
- `routers/encounters.py:28` (`POST /api/v1/compendium/encounters/balance`): no check. The route computes a balance from request input. It stores nothing.

## Documentation & Architecture Review
- ADR-0001: homebrew rule objects are `homebrew_rule`. Viewing uses `homebrew_rule.view`, which is `campaign->view` or `author`. Managing uses `homebrew_rule.manage`.
- ADR-0007: the compendium context owns SRD and homebrew rule data. The campaign relation is written by the campaign context and read here.
- ADR-0014: the blackbox test for this task uses only public routes.
- `docs/how-to/balance-combat-encounters-and-query-compendium.md` describes these routes and the `x-user-id` header. Replace the header text with the verified principal.
- The compendium stores homebrew in memory and can replace SRD entries (`w2-rules-compendium.md` F4, F5). Those findings are not authorization and are out of this task. The index report records them.

## Product & User Story References
- US-0052 (homebrew spell, monster, and rule authoring). US-0037 (CR encounter balancing and compendium). PRD-0008 (rules compendium and encounter builder).

## Detailed Specification & Implementation Plan
1. `dependencies.py` (the principal comes from TASK-0527):
   - The header read is removed by TASK-0527. Confirm it is gone.
   - `check_user_can_view_campaign` returns False for a missing principal. The SRD path does not call it.
   - `check_user_can_manage_homebrew` uses `homebrew_rule.manage` on the rule when the rule exists, and `campaign.manage` or `campaign.run_session` on the campaign for a new rule.
   - Delete the local `get_spicedb_client` and import the library factory.
2. Homebrew list (`GET`): a caller with no principal gets SRD results only. A caller with a principal gets the homebrew whose `homebrew_rule.view` check passes.
3. Search (`routers/rules.py`): same rule as the list. Anonymous search with `campaign_id` returns SRD results only.
4. Homebrew write (`POST`): writes `homebrew_rule:<id>#campaign@campaign:<cid>` and `homebrew_rule:<id>#author@user:<principal>`. A write error returns 503 and the rule is not saved.
5. Encounter balance: no change in auth. The route accepts an anonymous call only when no campaign is given. With a campaign id it requires `campaign.play`.

## Frontdoor Blackbox Test Plan
Setup: a campaign with a DM and a player. The DM creates a homebrew rule through `POST /api/v1/compendium/homebrew`. Roles come from the campaign role route (TASK-0543).
- Before the fix, anonymous `GET` of the campaign homebrew list returns the rule. After the fix it returns SRD results only and no homebrew.
- Anonymous search with `campaign_id` returns no homebrew hit.
- A player with no principal `POST`s a homebrew rule: 401. Before the fix a spoofed `x-user-id` returns 200.
- A player who is not a campaign member `POST`s: 403. The DM: 200.
- Setup through public routes only. No direct tuple write.

## Definition of Done
1. Frontdoor tests exist in `tests/test_blackbox_compendium_authz.py` and pass against the live harness.
2. `grep -rn "x-user-id\|\"secret\"\|spicedb_token" services/rules_compendium/src` returns nothing.
3. The compendium how-to is updated.
4. `uv run pytest services/rules_compendium` passes. `uv run ruff check services/rules_compendium` passes.
5. No file in the change exceeds 500 lines.

## Audit Provenance

- Severity: high
- Source audits: `w2-rules-compendium.md`, `w3-authz-coverage.md`
