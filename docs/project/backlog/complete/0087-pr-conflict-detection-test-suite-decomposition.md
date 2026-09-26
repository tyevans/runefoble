---
id: 0087
title: PR Conflict Detection and Stale Recovery Test Suite Modular Decomposition
status: Complete
created: 2026-09-26
dependencies:
- TASK-0046
governing_adrs:
- ADR-0007
- ADR-0008
- ADR-0009
target_release: 0.2.0
pr_url: https://github.com/tyevans/runefoble/pull/58
---
# TASK-0087: PR Conflict Detection and Stale Recovery Test Suite Modular Decomposition

## Status
Refined

## Summary
Decompose `tests/test_pr_conflict_detection.py` (465 lines, 93.0% of limit) into three specialized, single-responsibility test suites (`tests/test_backlog_ci_watcher.py`, `tests/test_backlog_stale_recovery.py`, and `tests/test_backlog_pr_repair.py`) to prevent breaching Hard Invariant 6 (File length limit < 500 lines) and improve CI feedback speed.

## Problem Statement
`tests/test_pr_conflict_detection.py` currently stands at 465 lines—the largest test file in the entire repository—placing it within 35 lines of breaching the 500-line hard invariant ceiling. The test suite conflates three distinct automation responsibilities:
1. Low-level CI status checking and GitHub CLI command parsing (`check_pr_conflict_status`, `wait_for_ci_checks`, `close_pull_request`, `fetch_failed_ci_logs`).
2. Stale task recovery, re-enqueuing mechanics, and pipeline retry circuit breakers (`recover_stale_tasks`, `requeue_failed_tasks`, task attempt limits).
3. End-to-end pull request watching, AI agent repair dispatch in isolated worktrees, and mid-flight git merge conflict resolution (`watch_and_repair_pull_request`).

As the backlog automation engine adds further CI healing diagnostics or multi-branch sync checks, this test suite will rapidly breach Hard Invariant 6.

## Governing Architecture & ADRs
- **ADR-0007**: Development Tooling and Local Kind Cluster Workflows (developer tool test hygiene).
- **ADR-0008**: Property and Mutation Testing Strategy (deterministic test isolation).
- **ADR-0009**: Code Quality and Linting with Ruff (strict file length invariant < 500 lines).

## Proposed Decomposition
1. **CI Watcher & Status Polling Suite (`tests/test_backlog_ci_watcher.py`)**:
   - `test_check_pr_conflict_status_clean`, `test_check_pr_conflict_status_conflicting`, `test_check_pr_conflict_status_closed`.
   - `test_wait_for_ci_checks_detects_conflict_immediately`, `test_close_pull_request`.
   - `test_fetch_failed_ci_logs_extracts_run_logs`.
   - Target length: < 150 lines.
2. **Stale Recovery & Retry Circuit Breaker Suite (`tests/test_backlog_stale_recovery.py`)**:
   - `test_recover_stale_tasks_recovers_review_status`, `test_recover_stale_tasks_recovers_in_progress_status`.
   - `test_requeue_failed_tasks_moves_from_review_to_refined`.
   - `test_run_orchestrator_drain_hits_failure_limit_and_stops`.
   - Target length: < 160 lines.
3. **PR Repair & Merge Conflict Resolution Suite (`tests/test_backlog_pr_repair.py`)**:
   - `test_watch_and_repair_pull_request_heals_ci_failure`.
   - `test_watch_and_repair_pull_request_heals_merge_conflict`.
   - Target length: < 160 lines.
4. **Original Monolith Deletion**:
   - Remove `tests/test_pr_conflict_detection.py`.

## INVEST Criteria Evaluation
- **Independent (I)**: Decomposes test file layout without altering runtime behavior in `tools/backlog_engine`.
- **Negotiable (N)**: Split boundaries between CI polling and recovery orchestration can be adjusted.
- **Valuable (V)**: Protects against Hard Invariant 6 violations (< 500 lines) and accelerates local test runs with modular targeting.
- **Estimable (E)**: Pure pytest suite decomposition with fixture sharing.
- **Small (S)**: Scope strictly isolated to `tests/test_pr_conflict_detection.py`; all resulting files < 170 lines.
- **Testable (T)**: `uv run pytest tests/test_backlog_ci_watcher.py tests/test_backlog_stale_recovery.py tests/test_backlog_pr_repair.py` confirms 100% pass rate with zero regression.

## Definition of Done (Hard Invariant 7: Blackbox TDD with Frontdoor Setup)
1. **Modular Test Suite Creation**:
   - `tests/test_backlog_ci_watcher.py`, `tests/test_backlog_stale_recovery.py`, and `tests/test_backlog_pr_repair.py` created with clear responsibility separation.
   - Original monolith `tests/test_pr_conflict_detection.py` deleted.
2. **Zero Test Coverage Regression**:
   - All 11 existing test cases preserved and passing with zero skips or muted assertions.
3. **File Length Compliance (Hard Invariant 6)**:
   - All resulting test files strictly under 200 lines.
4. **Frontdoor Test Execution**:
   - 100% pass rate on `uv run pytest tests/test_backlog_ci_watcher.py tests/test_backlog_stale_recovery.py tests/test_backlog_pr_repair.py`.
5. **Quality Gates**:
   - Passes `uv run ruff check tests/` and `uv run ruff format --check tests/`.
