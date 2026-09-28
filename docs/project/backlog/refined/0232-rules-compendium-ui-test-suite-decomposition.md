---
id: '0232'
title: Rules Compendium UI Blackbox Test Suite Modular Decomposition
status: Refined
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
Refined

## Summary
Decompose `tests/test_blackbox_rules_compendium_ui.py` (393 lines, 78.6% of limit - approaching the 500-line invariant limit) into modular test submodules under `tests/test_blackbox_rules_compendium_ui/` (`conftest.py`, `test_srd_search.py`, `test_homebrew_form.py`, and `test_encounter_cr.py`), keeping all test files strictly < 150 lines per Hard Invariant 6, ADR-0003, and ADR-0013.

## Problem Statement
`tests/test_blackbox_rules_compendium_ui.py` has grown to 393 lines, combining tests for SRD compendium hybrid search, homebrew creation forms, challenge rating balancing calculations, and microfrontend manifest registration in a single test module. Approaching the file size threshold, decomposing it into focused submodules ensures maintainability, fast test execution, and strict compliance with Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean modular test package structure under `tests/`.
- **ADR-0004: Lit Web Components and Storybook UI**: Microfrontend DOM contract and event testing.
- **ADR-0013: Microfrontend Architecture and Service Component Vendoring**: Isolated microfrontend test suites.

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_rules_compendium_ui/conftest.py`)**:
   - Extract test client, mock compendium service, and test entity fixtures (< 60 lines).
2. **SRD Search Tests (`tests/test_blackbox_rules_compendium_ui/test_srd_search.py`)**:
   - Verify SRD keyword search, filtering by category, and sub-50ms hybrid queries (< 100 lines).
3. **Homebrew Form Tests (`tests/test_blackbox_rules_compendium_ui/test_homebrew_form.py`)**:
   - Verify homebrew spell/item creation and validation (< 100 lines).
4. **Encounter CR Tests (`tests/test_blackbox_rules_compendium_ui/test_encounter_cr.py`)**:
   - Verify encounter difficulty thresholds and monster CR summation (< 100 lines).
5. **Verification**:
   - Remove root monolithic test module and run `uv run pytest tests/test_blackbox_rules_compendium_ui/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring is strictly isolated to test suite decomposition.
- **Negotiable (N)**: All existing test cases, assertions, and test coverage remain intact.
- **Valuable (V)**: Prevents test file from breaching the 500-line limit and speeds up targeted test execution.
- **Estimable (E)**: Pure mechanical decomposition of existing pytest functions into submodules.
- **Small (S)**: Scope restricted to separating test cases into 4 submodules (< 150 lines each).
- **Testable (T)**: Frontdoor validation via running the full pytest suite.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `tests/test_blackbox_rules_compendium_ui/` package created with all files strictly < 150 lines.
   - Monolithic `tests/test_blackbox_rules_compendium_ui.py` removed.
2. **Frontdoor Verification**:
   - All tests pass cleanly via `uv run pytest tests/test_blackbox_rules_compendium_ui/`.
3. **Quality Gates**:
   - Code formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
