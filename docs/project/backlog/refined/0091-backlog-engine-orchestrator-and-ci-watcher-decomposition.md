---
id: '0091'
title: Backlog Engine Orchestrator and CI Watcher Modular Decomposition
status: Refined
created: 2026-09-26
dependencies:
- TASK-0046
governing_adrs:
- ADR-0007
- ADR-0009
target_release: 0.2.0
---

# TASK-0091: Backlog Engine Orchestrator and CI Watcher Modular Decomposition

## Status
Refined

## Summary
Decompose `tools/backlog_engine/orchestrator.py` (447 lines, 89.4% of limit) and `tools/backlog_engine/ci_watcher.py` (432 lines, 86.4% of limit) into specialized, single-responsibility submodules to prevent breaching Hard Invariant 6 (File length limit < 500 lines).

## Problem Statement
`tools/backlog_engine` provides developer and CI automation for orchestrating worktrees, dispatching agent workers, polling CI, and merging PRs. Two files in this package are rapidly approaching the 500-line limit:
1. `tools/backlog_engine/orchestrator.py` (447 lines): Conflates pipeline lifecycle loops, worktree allocation, branch management, merge conflict detection, and queue drain mechanics.
2. `tools/backlog_engine/ci_watcher.py` (432 lines): Conflates GitHub CLI (`gh`) interaction, check run polling, log retrieval, error classification, and agent repair prompting.

Both files are within 50–70 lines of violating Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0003**: UV Monorepo Workspace for Python Bounded Contexts.
- **ADR-0009**: Continuous Backlog Refinement and Technical Debt Management.

## Proposed Decomposition
1. **GitHub API Client Module (`tools/backlog_engine/github_client.py`)**:
   - Extract CLI subprocess wrappers for `gh pr`, check-runs, log extraction, and issue comments (< 160 lines).
2. **CI Watcher & Diagnostic Repair (`tools/backlog_engine/ci_watcher.py`)**:
   - Retain polling loops, status checks, error diagnostics, and repair dispatcher, utilizing `github_client.py` (< 200 lines).
3. **Branch & Git Merge Handler (`tools/backlog_engine/git_ops.py`)**:
   - Extract Git worktree creation, branch checkout, conflict rebasing, and atomic merge execution (< 160 lines).
4. **Orchestrator Lifecycle Coordinator (`tools/backlog_engine/orchestrator.py`)**:
   - Retain task queue monitoring, worker pool concurrency management, and drain loops (< 220 lines).

## INVEST Criteria Evaluation
- **Independent (I)**: Internal refactor of `tools/backlog_engine/` without changing CLI interface (`python3 -m tools.backlog_engine.cli`).
- **Negotiable (N)**: Function boundaries between `git_ops.py` and `github_client.py` can be tuned.
- **Valuable (V)**: Protects developer tooling from breaching the 500-line hard invariant.
- **Estimable (E)**: Standard module separation with zero external dependency changes.
- **Small (S)**: Scope strictly isolated to `tools/backlog_engine/`; all resulting files < 250 lines.
- **Testable (T)**: Existing test suites (`tests/test_backlog_*.py` and `tests/test_pr_conflict_detection.py`) verify complete automation flow.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Submodule Creation**:
   - `github_client.py` and `git_ops.py` created with clean separation of GitHub API operations and git worktree tasks.
   - `orchestrator.py` and `ci_watcher.py` streamlined into high-level coordinators.
2. **Strict File Length Compliance (Hard Invariant 6)**:
   - All modified and newly created source files strictly under 250 lines.
3. **Frontdoor Blackbox Verification**:
   - 100% test pass rate across `tests/test_backlog_orchestrator.py`, `tests/test_backlog_ci_watcher.py`, and `tests/test_pr_conflict_detection.py`.
4. **Quality Gates**:
   - Passes `uv run ruff check tools/backlog_engine` and `uv run ruff format --check tools/backlog_engine`.
