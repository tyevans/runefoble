---
id: '0232'
title: Rules Compendium UI Blackbox Test Suite Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0048
- TASK-0108
governing_adrs:
- ADR-0003
- ADR-0004
- ADR-0013
governing_prds:
- PRD-0008
governing_stories:
- US-0037
- US-0052
target_release: 0.8.0
---

# TASK-0232: Rules Compendium UI Blackbox Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_blackbox_rules_compendium_ui.py` (319 lines, 63.8% of limit) into modular test submodules under `tests/test_blackbox_rules_compendium_ui/` (`conftest.py`, `test_srd_search.py`, `test_homebrew_form.py`, `test_encounter_cr.py`), keeping all test files strictly < 150 lines per Hard Invariant 6.

## Problem Statement
`tests/test_blackbox_rules_compendium_ui.py` tests SRD compendium hybrid search, homebrew creation forms, challenge rating balancing, and microfrontend manifest registration in a single 319-line file. Approaching the file size limit, it should be decomposed into focused submodules.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test package structure.
- **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend DOM contract testing.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Isolated microfrontend test suites.

## Scope of Work
1. **Shared Fixtures (`tests/test_blackbox_rules_compendium_ui/conftest.py`)**:
   - Extract test client, mock compendium service, and test entity fixtures (< 60 lines).
2. **SRD Search Tests (`tests/test_blackbox_rules_compendium_ui/test_srd_search.py`)**:
   - Verify SRD keyword search, filtering by category, and sub-50ms hybrid queries (< 100 lines).
3. **Homebrew Form Tests (`tests/test_blackbox_rules_compendium_ui/test_homebrew_form.py`)**:
   - Verify homebrew spell/item creation and validation (< 100 lines).
4. **Encounter CR Tests (`tests/test_blackbox_rules_compendium_ui/test_encounter_cr.py`)**:
   - Verify encounter difficulty thresholds and monster CR summation (< 100 lines).
5. **Verification**:
   - Remove root test module and run `uv run pytest tests/test_blackbox_rules_compendium_ui/`.

## Definition of Done
- `tests/test_blackbox_rules_compendium_ui/` package created with all files strictly < 150 lines.
- Zero files in test suite exceed 150 lines.
- Passes `uv run pytest tests/test_blackbox_rules_compendium_ui/`.
- Code passes `uv run ruff check .` and `uv run ruff format --check .`.
