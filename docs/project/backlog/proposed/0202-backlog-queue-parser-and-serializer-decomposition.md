---
id: '0202'
title: Backlog Queue Parser and Serializer Modular Decomposition
status: Proposed
created: 2026-09-27
dependencies:
- TASK-0091
governing_adrs:
- ADR-0003
- ADR-0007
governing_prds: []
governing_stories: []
target_release: 0.7.0
---

# TASK-0202: Backlog Queue Parser and Serializer Modular Decomposition

## Status
Proposed

## Summary
Decompose `tools/backlog_engine/queue.py` (375 lines, 75.0% of limit) into modular submodules under `tools/backlog_engine/` (`parser.py` and `serializer.py`), extracting task markdown frontmatter parsing and serialized file writing out of the queue coordinator, keeping all files strictly < 180 lines per Hard Invariant 6.

## Problem Statement
`tools/backlog_engine/queue.py` has grown to 375 lines by combining YAML frontmatter regex extraction, priority map rank loading, markdown writing with atomic frontmatter updates, and queue state lifecycle operations (`claim_next_task`, `complete_task`, `unclaim_task`, `list_all_tasks`). As additional metadata validation hooks, worktree tracking, and automated JIT triage are added, this file will rapidly approach the 500-line invariant limit unless decoupled.

## Governing Architecture & ADRs
- **ADR-0003: UV Monorepo Workspace for Python BCs**: Clean module layout and single-responsibility Python modules.
- **ADR-0007: Domain-Driven Design Architecture**: Clean domain segregation between file parsing/serialization and queue lifecycle state transitions.

## Scope of Work
1. **Parser Submodule (`tools/backlog_engine/parser.py`)**:
   - Extract `FRONTMATTER_PATTERN`, `parse_task_file`, and `load_priority_map` (< 120 lines).
2. **Serializer Submodule (`tools/backlog_engine/serializer.py`)**:
   - Extract `write_task_file` and frontmatter YAML formatting routines (< 70 lines).
3. **Queue Coordinator (`tools/backlog_engine/queue.py`)**:
   - Focus `BacklogQueue` strictly on queue discovery, dependency resolution, and atomic state transitions, delegating parsing and serialization to the submodules (< 180 lines).
4. **Verification**:
   - Run backlog engine test suites (`tests/test_blackbox_backlog_engine/` and unit tests) to verify 100% test compatibility.

## Definition of Done
- `tools/backlog_engine/queue.py` reduced to < 180 lines.
- `parser.py` and `serializer.py` created and strictly < 150 lines each.
- All backlog engine tests pass cleanly via `uv run pytest`.
- Code formatted and linted cleanly via `uv run ruff check .` and `uv run ruff format --check .`.
