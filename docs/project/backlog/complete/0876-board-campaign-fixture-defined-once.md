---
id: '0876'
title: Board Campaign Fixture Is Defined Once in the Shared Campaign Helper
status: Complete
created: 2026-11-18
dependencies: []
governing_adrs:
- ADR-0014
governing_prds: []
governing_stories: []
target_bc: core
target_release: 0.9.0
---
# TASK-0876: Board Campaign Fixture Is Defined Once in the Shared Campaign Helper

## Status
Complete

## Summary
Twenty-eight test files under `tests/` and `gateway/api/tests/` define the same `board_campaign` fixture. Each one returns `create_dm_campaign("user-test")`. Define the fixture once in the shared campaign helper, and register it in the root `conftest.py`.

## Problem Statement
- Twenty-eight files define `board_campaign`. Examples: `tests/test_blackbox_tactile_board.py:153`, `tests/test_blackbox_board_get_frontdoor.py:130`, `tests/test_blackbox_board_state.py:104`, `tests/test_blackbox_board_routers.py:208`, `tests/test_blackbox_mcp_create_encounter.py:192`, `tests/test_tactile_board_kinematics.py:124`.
- Each copy returns `create_dm_campaign("user-test")`, except `tests/test_blackbox_board_spell_cast_events.py:33`, which uses its own DM id.
- `create_dm_campaign` already exists at `tests/helpers/campaign_setup.py:78`.
- TASK-0697 and TASK-0769 are complete. They moved the service fixtures, but these copies remain.

## Documentation & Architecture Review
- ADR-0014 (blackbox setup through frontdoors). `create_dm_campaign` creates the campaign through the public route.
- Root `conftest.py` `pytest_plugins` applies to all test folders.

## Product & User Story References
None. Test helper work.

## Detailed Specification & Implementation Plan
1. Define `board_campaign` once in `tests/helpers/campaign_setup.py`. It returns `create_dm_campaign("user-test")`.
2. Add `tests.helpers.campaign_setup` to the `pytest_plugins` list in the root `conftest.py`.
3. Delete the twenty-eight copies.
4. In `test_blackbox_board_spell_cast_events.py`, keep one local fixture that calls `create_dm_campaign` with its own DM id.

## Frontdoor Blackbox Test Plan
- The twenty-eight suites pass unchanged.

## Definition of Done
- One `def board_campaign` in `tests/` and `gateway/api/tests/`, outside the spell-cast file.
- `uv run pytest` passes. No file over 500 lines.
- No backward-compatibility shim (DoR 9).

## Audit Provenance
- Severity: low
- Source audits: `tests`
