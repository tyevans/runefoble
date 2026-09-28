---
id: '0202'
title: Backlog Queue Parser and Serializer Modular Decomposition
status: Complete
created: 2026-09-27
dependencies:
- TASK-0091
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.7.0
pr_url: https://github.com/tyevans/runefoble/pull/266
---
# TASK-0202: Backlog Queue Parser and Serializer Modular Decomposition

## Status
Refined

## Summary
Decompose `tools/backlog_engine/queue.py` (374 lines, 74.8% of limit) into modular submodules under `tools/backlog_engine/` (`parser.py`, `serializer.py`, and `queue.py`), extracting task markdown frontmatter parsing and serialized file writing out of the queue coordinator, keeping all files strictly < 180 lines per Hard Invariant 6, ADR-0003, and ADR-0007.

## Problem Statement
`tools/backlog_engine/queue.py` has grown to 374 lines by combining YAML frontmatter regex extraction, priority map rank loading, markdown writing with atomic frontmatter updates, and queue state lifecycle operations (`claim_next_task`, `complete_task`, `unclaim_task`, `list_all_tasks`). As additional metadata validation hooks, worktree tracking, and automated JIT triage are added, this file will rapidly approach the 500-line invariant limit unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and single-responsibility Python modules.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between file parsing/serialization and queue lifecycle state transitions.

## Detailed Specification & Implementation Plan
1. **Parser Submodule (`tools/backlog_engine/parser.py`)**:
   - Extract `FRONTMATTER_PATTERN`, `parse_task_file`, and `load_priority_map` (< 120 lines).
   - Ensure resilient parsing of frontmatter YAML blocks and priority indices without external dependencies.
2. **Serializer Submodule (`tools/backlog_engine/serializer.py`)**:
   - Extract `write_task_file` and frontmatter YAML formatting routines (< 70 lines).
   - Preserve markdown body formatting, metadata attributes, and atomic write semantics.
3. **Queue Coordinator Refactoring (`tools/backlog_engine/queue.py`)**:
   - Focus `BacklogQueue` strictly on task discovery, dependency graph resolution, priority sorting, and atomic state transitions, delegating parsing and serialization to the submodules (< 180 lines).
4. **Verification**:
   - Run backlog engine test suites (`tests/test_blackbox_backlog_engine/` and unit tests) to verify 100% test compatibility.

## INVEST Criteria Evaluation
- **Independent (I)**: Refactoring is strictly isolated to `tools/backlog_engine/` internal modules.
- **Negotiable (N)**: Function signatures and public methods on `BacklogQueue` remain unchanged.
- **Valuable (V)**: Prevents hard invariant breaches and decouples file I/O from queue orchestration.
- **Estimable (E)**: Pure refactoring of existing, well-tested Python logic.
- **Small (S)**: Scope restricted to separating three distinct responsibilities (< 180 lines per file).
- **Testable (T)**: Frontdoor verification through the backlog CLI commands and blackbox test suites.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Module Architecture**:
   - `tools/backlog_engine/queue.py` reduced to < 180 lines.
   - `tools/backlog_engine/parser.py` and `tools/backlog_engine/serializer.py` created and strictly < 150 lines each.
2. **Frontdoor Verification**:
   - All backlog engine CLI commands (`list`, `status`, `claim`, `complete`) work without error.
   - All backlog engine blackbox tests pass via `uv run pytest tests/test_blackbox_backlog_engine/`.
3. **Quality Gates**:
   - Code formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
