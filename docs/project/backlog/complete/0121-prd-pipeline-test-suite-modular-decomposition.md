---
id: '0121'
title: PRD Pipeline Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0119
governing_adrs:
- ADR-0003
- ADR-0009
target_release: 0.4.0
pr_url: https://github.com/tyevans/runefoble/pull/134
---
# TASK-0121: PRD Pipeline Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_prd_pipeline.py` (418 lines) into discrete, single-responsibility test modules (`test_prd_manager.py`, `test_prd_planner.py`, and `test_prd_decomposer.py`), keeping all test files strictly under 250 lines and preserving 100% test coverage.

## Problem Statement
`tests/test_prd_pipeline.py` currently spans 418 lines, approaching the 500-line hard invariant limit (Hard Invariant 6). It consolidates PRD creation, template rendering, decomposition planning, task slice generation, and CLI parsing in a single monolithic test file.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Standardized test structuring within monorepo.
- **ADR-0009: Code Quality and Linting with Ruff and Pre-commit**: Clean modular separation and test isolation.

## Detailed Specification & Implementation Plan
1. **Manager & Registry Suite (`tests/test_prd_pipeline_manager.py`)**:
   - Tests for `PRDManager`, PRD numbering, directory structure initialization, and registry auditing (< 150 lines).
2. **Planner & Slice Analysis Suite (`tests/test_prd_pipeline_planner.py`)**:
   - Tests for `DecompositionPlanner`, spike detection, UI component detection, and worker slice detection (< 150 lines).
3. **Decomposer & Task Writer Suite (`tests/test_prd_pipeline_decomposer.py`)**:
   - Tests for `PRDDecomposer`, `PlanWriter`, YAML frontmatter serialization, and task file drafting (< 150 lines).
4. **CLI & Smoke Suite (`tests/test_prd_pipeline_cli.py`)**:
   - Tests for CLI argument parsing, interactive modes, and error exits (< 120 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Pure test suite refactoring without modifying tool business logic or CLI output.
- **Negotiable (N)**: Split boundaries between planner and decomposer tests can be tuned.
- **Valuable (V)**: Protects codebase health against invariant breaches and improves test maintainability.
- **Estimable (E)**: Straightforward file decomposition of existing pytest cases.
- **Small (S)**: Scope strictly isolated to `tests/`; all resulting files < 200 lines.
- **Testable (T)**: Verified by running `uv run pytest tests/test_prd_pipeline*.py`.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Decomposed Modules**:
   - `tests/test_prd_pipeline.py` eliminated; replacement test files each strictly < 250 lines.
2. **Zero Regressions**:
   - 100% of existing PRD pipeline assertions pass without modification.
3. **Quality Gates**:
   - Hard Invariant 6 met with zero files exceeding 500 lines.
   - Passes `uv run pytest tests/test_prd_pipeline*.py` and `uv run ruff check .`.
