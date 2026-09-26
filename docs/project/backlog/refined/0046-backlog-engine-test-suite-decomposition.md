---
id: '0046'
title: Backlog Engine Test Suite Modular Decomposition
status: Refined
created: 2026-09-26
dependencies: [TASK-0000]
governing_adrs: [ADR-0007, ADR-0008, ADR-0009]
target_release: 0.2.0
---

# TASK-0046: Backlog Engine Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_backlog_engine.py` (476 lines, 95.2% of limit) into three focused, modular test suites (`tests/test_backlog_parser.py`, `tests/test_backlog_queue.py`, and `tests/test_backlog_execution.py`) before breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tests/test_backlog_engine.py` currently stands at 476 lines, placing it within 24 lines of breaching the 500-line hard invariant ceiling. As the largest file in the entire repository, any additional backlog validation checks or schema tests will trigger CI invariant failures. The monolithic file bundles three disparate concerns:
1. Markdown frontmatter and YAML parsing, octal number safety, and ADR citation extraction.
2. Topological task sorting, circular dependency detection, and priority queue ordering.
3. Subprocess execution, automated quality gate validation, rollback semantics, and status progression.

## INVEST Criteria Evaluation
- **Independent (I)**: Splits test suite structure without modifying backlog engine core libraries or runner behavior.
- **Negotiable (N)**: Split boundaries and fixture sharing across pytest test files can be adjusted.
- **Valuable (V)**: Prevents CI test suite invariant failures, ensures maintainability, and improves test execution parallelism.
- **Estimable (E)**: Pure test suite refactoring using standard pytest fixtures and runner invocations.
- **Small (S)**: Scope strictly isolated to `tests/test_backlog_engine.py`; all three resulting test files will remain under 200 lines.
- **Testable (T)**: `uv run pytest tests/test_backlog_*.py` verifies 100% test pass rate with zero test regression.

## Governing Architecture & ADRs
- **ADR-0007**: Development Tooling & Local Kind Cluster Workflows (developer test tooling, task execution engine).
- **ADR-0008**: Property and Mutation Testing Strategy (deterministic test suites, modular isolation).
- **ADR-0009**: Code Quality and Linting with Ruff and Pre-Commit (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **Parser & Frontmatter Validation Suite (`tests/test_backlog_parser.py`)**:
   - `test_parse_task_file_octal_safety`, frontmatter YAML schema validation, and DoD section parsing (< 150 lines).
2. **Queue & Topological Dependency Suite (`tests/test_backlog_queue.py`)**:
   - Priority queue ordering, topological sorting, unmet dependency blocking, and circular dependency cycle detection (< 160 lines).
3. **Engine Execution Suite (`tests/test_backlog_execution.py`)**:
   - Task status transitions, automated gate validation, rollback hooks, and registry updates (< 180 lines).

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Creation**:
   - `tests/test_backlog_parser.py` created and dedicated to frontmatter/syntax parsing.
   - `tests/test_backlog_queue.py` created and dedicated to topological queue sorting and cycle detection.
   - `tests/test_backlog_execution.py` created and dedicated to engine runner execution and lifecycle gates.
   - Original monolithic `tests/test_backlog_engine.py` removed.
2. **Zero Coverage Loss**:
   - 100% of existing test scenarios, edge cases, and assertions preserved without skipped tests.
3. **File Length Compliance**:
   - All three test files strictly < 200 lines (well under the 500-line ceiling).
4. **Frontdoor Blackbox Verification**:
   - 100% pass rate on `uv run pytest tests/test_backlog_parser.py tests/test_backlog_queue.py tests/test_backlog_execution.py`.
5. **Quality Gate Verification**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
