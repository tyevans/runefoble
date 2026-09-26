---
id: '0046'
title: Backlog Engine Test Suite Modular Decomposition
status: Proposed
created: 2026-09-26
dependencies: [TASK-0000]
governing_adrs: [ADR-0007]
target_release: 0.2.0
---

# TASK-0046: Backlog Engine Test Suite Modular Decomposition

## Status
Proposed

## Summary
Decompose `tests/test_backlog_engine.py` (469 lines, 93.8% of limit) into modular test suites (`test_backlog_parser.py`, `test_backlog_queue.py`, and `test_backlog_execution.py`) before breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tests/test_backlog_engine.py` has grown to 469 lines, placing it within 31 lines of breaching the 500-line hard invariant ceiling. The test module currently covers:
1. Markdown frontmatter and YAML parsing, octal number safety, and ADR citation extraction.
2. Topological task sorting, circular dependency detection, and priority queue ordering.
3. Subprocess execution, quality gate validation, rollback semantics, and status progression.

## Proposed Decomposition
1. **Parser & Validation Suite (`tests/test_backlog_parser.py`)**:
   - `test_parse_task_file_octal_safety`, frontmatter schema validation, and DoD section checks (< 150 lines).
2. **Queue & Dependency Suite (`tests/test_backlog_queue.py`)**:
   - Priority queue ordering, topological sorting, unmet dependency blocking, and circular dependency cycle detection (< 160 lines).
3. **Engine Execution Suite (`tests/test_backlog_execution.py`)**:
   - Task status transitions, automated gate validation, rollback hooks, and registry updates (< 180 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Splits test suite structure without modifying backlog engine core libraries or runner behavior.
- **Negotiable (N)**: Split boundaries and fixture sharing across pytest test files can be adjusted.
- **Valuable (V)**: Prevents CI test suite invariant failures and improves test execution parallelism and maintainability.
- **Estimable (E)**: Pure test suite refactoring using pytest fixtures.
- **Small (S)**: Scope strictly isolated to `tests/test_backlog_engine.py`.
- **Testable (T)**: `pytest tests/test_backlog_*.py` verifies 100% test pass rate with zero test regression.

## Acceptance Criteria
1. Zero loss of test coverage or test scenarios across backlog engine features.
2. All resulting test files strictly under 250 lines.
3. Conforms to Hard Invariant 6 (< 500 lines per file).
