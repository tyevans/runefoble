---
id: '0283'
title: Lobby and VTT Character Sync Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-28
dependencies:
- TASK-0256
governing_adrs:
- ADR-0004
- ADR-0007
- ADR-0012
- ADR-0013
governing_prds:
- PRD-0023
governing_stories:
- US-0065
- US-0069
target_release: 0.8.0
---

# TASK-0283: Lobby and VTT Character Sync Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_lobby_and_vtt_character_sync.py` (330 lines, 66.0% of limit) into modular test submodules under `tests/test_blackbox_lobby_and_vtt_character_sync/` (`conftest.py`, `test_invariants.py`, `test_frontdoor_api.py`, `test_resolution_logic.py`), ensuring all test submodules remain strictly < 130 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_lobby_and_vtt_character_sync.py` tests line count invariants, Bauhaus design token compliance, custom element contract declarations, gateway character API frontdoors, and multi-scenario character fallback resolution in a single 330-line file. As multi-party stand-in and hot-swap synchronization test cases are added, this test file will breach the 500-line limit unless decomposed into focused, single-responsibility submodules.

## Governing Architecture & ADRs
- **ADR-0004: Lit Web Components and Storybook UI**: Dynamic property contracts and shadow DOM events.
- **ADR-0007: Domain-Driven Design Architecture**: Clean frontdoor testing and aggregate boundaries.
- **ADR-0012: Design System Theming and Bauhaus Modernism**: Design token adherence and zero hex literals.
- **ADR-0013: Frontend Microfrontend Architecture**: Microfrontend component contracts and shell binding.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_lobby_and_vtt_character_sync/conftest.py`)**:
   - Extract test client setup, store resets, and shared paths (< 50 lines).
2. **Invariant & Token Tests (`tests/test_blackbox_lobby_and_vtt_character_sync/test_invariants.py`)**:
   - Extract source file length invariants and Bauhaus design token assertion tests (< 80 lines).
3. **Component Contracts (`tests/test_blackbox_lobby_and_vtt_character_sync/test_component_contracts.py`)**:
   - Extract Lit custom element dynamic property declarations and app-data-service inspections (< 80 lines).
4. **Frontdoor API & Resolution (`tests/test_blackbox_lobby_and_vtt_character_sync/test_resolution_scenarios.py`)**:
   - Extract Gateway API CRUD and lobby-to-VTT session fallback resolution tests (< 110 lines).
5. **Verification**:
   - Remove root monolithic file and run `uv run pytest tests/test_blackbox_lobby_and_vtt_character_sync/`.

## Definition of Done
- `tests/test_blackbox_lobby_and_vtt_character_sync/` submodules strictly < 130 lines each.
- Root `tests/test_blackbox_lobby_and_vtt_character_sync.py` safely removed.
- Passes all tests via `uv run pytest tests/test_blackbox_lobby_and_vtt_character_sync/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
