---
id: '0298'
title: Character Roster Binding Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0254
governing_adrs:
- ADR-0001
- ADR-0004
- ADR-0007
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0064
- US-0069
target_release: 0.8.0
---

# TASK-0298: Character Roster Binding Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_character_roster_binding.py` (298 lines, 59.6% of limit) into modular test submodules under `tests/test_blackbox_character_roster_binding/` (`conftest.py`, `test_character_mutations.py`, `test_campaign_bindings.py`, `test_contract_invariants.py`), keeping all test files strictly < 110 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_character_roster_binding.py` validates character creation, campaign assignment, character deletion, inspection navigation, and frontend App Shell contracts in a single 298-line test file. As multi-character party management and inventory synchronization tests are added, this test suite will quickly breach the 500-line invariant limit unless structured into dedicated submodules.

## Governing Architecture & ADRs
- **ADR-0001: SpiceDB Zanzibar Object Authorization**: Verifies user-bound character permissions and campaign memberships.
- **ADR-0004: Bauhaus Geometric Design System**: Verifies component integration and design tokens.
- **ADR-0007: Domain-Driven Gateway**: Validates Gateway API endpoints and event-driven data flow.
- **ADR-0013: Modular Decomposition**: All source files kept strictly < 500 lines (submodules < 110 lines).

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_character_roster_binding/conftest.py`)**:
   - Extract test client setup, store resets, and mock fixtures (< 50 lines).
2. **Character Creation & Deletion Tests (`tests/test_blackbox_character_roster_binding/test_character_mutations.py`)**:
   - Extract `POST /api/v1/characters` creation and `DELETE /api/v1/characters/{id}` verification tests (< 90 lines).
3. **Campaign Assignment & Navigation Tests (`tests/test_blackbox_character_roster_binding/test_campaign_bindings.py`)**:
   - Extract campaign assignment mutation tests and sheet inspection navigation assertions (< 90 lines).
4. **Contract Invariants & File Structure Tests (`tests/test_blackbox_character_roster_binding/test_contract_invariants.py`)**:
   - Extract TypeScript contract validation and file length checks (< 80 lines).
5. **Verification**:
   - Safely remove monolithic `tests/test_blackbox_character_roster_binding.py` and run `uv run pytest tests/test_blackbox_character_roster_binding/`.

## Definition of Done
- `tests/test_blackbox_character_roster_binding.py` decomposed into `tests/test_blackbox_character_roster_binding/` package.
- All extracted test files strictly < 110 lines per Hard Invariant 6.
- 100% test passing via `uv run pytest tests/test_blackbox_character_roster_binding/`.
- Monolithic `tests/test_blackbox_character_roster_binding.py` safely removed.
