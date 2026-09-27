---
id: '0187'
title: Campaign Atlas Blackbox Test Suite Modular Decomposition
status: Refined
created: 2026-09-27
dependencies:
- TASK-0106
governing_adrs:
- ADR-0001
- ADR-0003
- ADR-0007
governing_prds:
- PRD-0015
governing_stories:
- US-0050
target_release: 0.7.0
---

# TASK-0187: Campaign Atlas Blackbox Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_blackbox_campaign_atlas.py` (346 lines, 69.2% of limit) into modular focused test suites under `tests/test_blackbox_campaign_atlas/` (`conftest.py`, `test_territories.py`, `test_pins.py`, `test_codex_links.py`), keeping all test modules strictly < 150 lines per Hard Invariant 6 and Hard Invariant 7.

## Problem Statement
`tests/test_blackbox_campaign_atlas.py` contains 346 lines verifying geopolitical territory definitions, polygon coordinate containment, milestone pin placements, era filtering, and codex cross-links in a single monolithic test file. With shared world frontier additions in Milestone 9, this test suite will expand beyond 400 lines unless decomposed into modular test suites.

## Governing Architecture & ADRs
- **ADR-0001: Zanzibar Fine-Grained Authorization with SpiceDB**: Access control verification on territory and pin access.
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean test module structure across workspace.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain separation between territory boundaries, atlas pins, and codex lore.

## Detailed Specification & Implementation Plan
1. **Shared Fixtures (`tests/test_blackbox_campaign_atlas/conftest.py`)**:
   - Extract mock SpiceDB Zanzibar client, test clients, geometry fixtures, and campaign context (< 60 lines).
2. **Territory Tests (`tests/test_blackbox_campaign_atlas/test_territories.py`)**:
   - Geopolitical boundary definitions, polygon containment queries, and contested territory updates (< 110 lines).
3. **Milestone Pin Tests (`tests/test_blackbox_campaign_atlas/test_pins.py`)**:
   - Milestone pin placement, pin coordinates, era filtering, and Zanzibar permission checks (< 110 lines).
4. **Codex Links Tests (`tests/test_blackbox_campaign_atlas/test_codex_links.py`)**:
   - Cross-linking pins to codex entries and shared world metadata (< 90 lines).
5. **Verification**:
   - Remove root test module `tests/test_blackbox_campaign_atlas.py` and run `uv run pytest tests/test_blackbox_campaign_atlas/`.

## INVEST Criteria Evaluation
- **Independent (I)**: Test refactoring isolated entirely to the `tests/test_blackbox_campaign_atlas/` package.
- **Negotiable (N)**: Test categorization follows natural domain boundaries (territories, pins, codex integration).
- **Valuable (V)**: Safeguards against Hard Invariant 6 (500 lines) and speeds up atlas test execution and maintenance.
- **Estimable (E)**: Deterministic extraction of test functions into discrete modules with shared `conftest.py`.
- **Small (S)**: Bounded strictly to `tests/test_blackbox_campaign_atlas/`; all modules < 150 lines.
- **Testable (T)**: Frontdoor verification through pytest test suite execution against public HTTP endpoints and domain events.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `test_blackbox_campaign_atlas.py` replaced by decomposed submodules under `tests/test_blackbox_campaign_atlas/`.
   - All extracted test files strictly < 150 lines per Hard Invariant 6.
2. **Frontdoor Test Verification**:
   - All tests pass via `uv run pytest tests/test_blackbox_campaign_atlas/`.
3. **Quality Gates**:
   - Code passes `uv run ruff check .` and `uv run ruff format --check .`.
