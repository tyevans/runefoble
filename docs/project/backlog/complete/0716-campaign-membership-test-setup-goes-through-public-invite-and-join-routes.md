---
id: '0716'
title: Campaign Membership Test Setup Goes Through Public Invite and Join Routes
status: Complete
created: 2026-11-17
dependencies:
- TASK-0697
governing_adrs:
- ADR-0014
- ADR-0015
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0716: Campaign Membership Test Setup Goes Through Public Invite and Join Routes

## Status
Complete

## Summary
`write_relationship` is called in 98 test files to seed SpiceDB tuples. This is backdoor setup. One frontdoor fixture must create a campaign and its members through public routes. This task builds the fixture and migrates the first group of files.

## Problem Statement
- `write_relationship` appears in 98 test or conftest files, for example `tests/test_blackbox_campaign_grants_authz.py`, `tests/test_blackbox_caravan_contracts/test_board_posting.py`, `tests/test_blackbox_settlements_integration/conftest.py:116`.
- `setup_campaign_settlement` seeds tuples with `asyncio.run(db.write_relationship(...))`.
- Partial overlap: TASK-0559 covers name contracts, not seeding.

## Documentation & Architecture Review
- AGENTS.md hard invariants and DoR 9 (no compatibility shims).
- ADR-0014, ADR-0015.
- `docs/how-to/` and `docs/reference/` pages named in the specification.

## Product & User Story References
None. Platform quality work.

## Detailed Specification & Implementation Plan
1. Add one fixture in the shared harness (TASK-0697) that mints tokens with `SIGNING_ISSUER`, creates a campaign, and adds members through the game_session invite and join routes.
2. Migrate the files in the `tests/test_blackbox_settlements_integration`, `tests/test_blackbox_settlement_haven`, and `tests/test_blackbox_caravan_contracts` directories.
3. Keep `write_relationship` only in tests whose subject is SpiceDB sync.
4. File a follow-up for the remaining files. List the count left in the PR.

## Frontdoor Blackbox Test Plan
- The migrated tests set up membership through the invite and join routes and assert access through the normal route that the membership grants.
- `grep -rn write_relationship` in the three directories shows none.

## Definition of Done
- The specification steps are done and the tests above pass.
- Docs named in the specification are corrected.
- `uv run pytest`, `make lint` and `make health-check` pass. No file over 500 lines.

## Audit Provenance
- Severity: medium
- Source audits: `refactor-r1/tests.md`

## Completion Note
The three named directories are done. The repository-wide remainder (132 files that call `write_relationship`) is TASK-0841.
