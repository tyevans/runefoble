---
id: '0286'
title: Character Management and VTT Sync Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0258
governing_adrs:
- ADR-0001
- ADR-0002
- ADR-0004
- ADR-0010
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0064
- US-0069
target_release: 0.8.0
---

# TASK-0286: Character Management and VTT Sync Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_character_management_and_vtt_sync.py` (310 lines, 62.0% of limit) into modular test submodules under `tests/test_blackbox_character_management_and_vtt_sync/` (`conftest.py`, `test_character_auth_and_crud.py`, `test_campaign_assignment.py`, `test_app_shell_contracts.py`), ensuring all test submodules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_character_management_and_vtt_sync.py` covers SpiceDB Zanzibar object authorization, Gateway character CRUD endpoints, campaign party assignments, profile settings deduplication, App Shell character card routing contracts, and TypeScript test subprocess executions in a single 310-line file. As multi-character party management and inventory synchronization edge cases expand, this test suite will approach the 500-line ceiling unless modularized.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Fine-Grained Authorization**: Character edit and view permission checks.
- **ADR-0002: Domain Events via eventsource-py**: Character lifecycle domain event testing.
- **ADR-0004: Lit Web Components and Storybook UI**: App Shell character sheet route and inspector contracts.
- **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component contracts.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_character_management_and_vtt_sync/conftest.py`)**:
   - Extract test client fixtures, store resets, and file path references (< 50 lines).
2. **Character CRUD & Auth (`tests/test_blackbox_character_management_and_vtt_sync/test_character_auth_and_crud.py`)**:
   - Extract character creation, updating, deletion, and SpiceDB Zanzibar permission checks (< 110 lines).
3. **Campaign Assignment & Roster (`tests/test_blackbox_character_management_and_vtt_sync/test_campaign_assignment.py`)**:
   - Extract campaign assignment, roster listing, and profile settings deduplication tests (< 110 lines).
4. **App Shell Contracts (`tests/test_blackbox_character_management_and_vtt_sync/test_app_shell_contracts.py`)**:
   - Extract App Shell routing inspection, character card custom element contracts, and TS test suite execution (< 90 lines).
5. **Verification**:
   - Remove root monolithic file and run `uv run pytest tests/test_blackbox_character_management_and_vtt_sync/`.

## Definition of Done
- `tests/test_blackbox_character_management_and_vtt_sync/` submodules strictly < 130 lines each.
- Root `tests/test_blackbox_character_management_and_vtt_sync.py` safely removed.
- Passes all tests via `uv run pytest tests/test_blackbox_character_management_and_vtt_sync/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
