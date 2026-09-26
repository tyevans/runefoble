"""Frontdoor blackbox tests for Backlog Engine Orchestrator lifecycle coordinator."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.backlog_engine.models import Task, TaskStatus
from tools.backlog_engine.orchestrator import (
    TaskExecutionResult,
    execute_task_pipeline,
    run_orchestrator,
)
from tools.backlog_engine.queue import BacklogQueue


def test_task_execution_result_initialization():
    """Verifies that TaskExecutionResult correctly records status and message."""
    task = Task(id="0091", title="Decomp", status=TaskStatus.READY, file_path=Path("0091.md"))
    res = TaskExecutionResult(task, True, "All gates green")
    assert res.task.id == "0091"
    assert res.success is True
    assert res.message == "All gates green"


def test_orchestrator_dry_run_exits_cleanly(tmp_path: Path):
    """Verifies that run_orchestrator in dry-run mode inspects tasks and exits without dispatching."""
    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    refined_dir = backlog_dir / "refined"
    refined_dir.mkdir(parents=True)
    task_file = refined_dir / "0091-modular.md"
    task_file.write_text(
        "---\nid: '0091'\ntitle: Modular Decomposition\nstatus: Refined\n---\n# TASK-0091\n",
        encoding="utf-8",
    )
    (backlog_dir / "PRIORITY.md").write_text(
        "1. **TASK-0091 (Refined)**: [0091-modular.md](refined/0091-modular.md)\n"
    )

    exit_code = run_orchestrator(repo_root=tmp_path, dry_run=True, drain=False)
    assert exit_code == 0
    # Task remains untouched in refined directory
    queue = BacklogQueue(backlog_dir)
    ready = queue.get_ready_unblocked_tasks()
    assert len(ready) == 1
    assert ready[0].id == "0091"


def test_execute_task_pipeline_success_local_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that execute_task_pipeline runs through worktree creation, preflight, and local merge."""
    task = Task(
        id="0091",
        title="Modular Decomposition",
        status=TaskStatus.READY,
        file_path=tmp_path / "0091.md",
    )
    mock_queue = MagicMock()

    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.create_worktree", lambda *a, **k: tmp_path / "wt"
    )
    monkeypatch.setattr("tools.backlog_engine.orchestrator.cleanup_worktree", lambda *a, **k: None)
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.sync_and_resolve_base_ref",
        lambda *a, **k: (True, "synced"),
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.run_preflight_checks", lambda wt: (True, "all passed")
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.merge_local_branch", lambda repo, branch, t: None
    )

    res = execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True, skip_agent=True)
    assert res.success is True
    assert "integrated successfully" in res.message
    mock_queue.claim_task.assert_called_once()
    mock_queue.complete_task.assert_called_once_with(task)


def test_orchestrator_parallel_dispatch_processes_multiple_streams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that run_orchestrator dispatches multiple tasks concurrently with threadpool."""
    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    refined_dir = backlog_dir / "refined"
    refined_dir.mkdir(parents=True)
    for tid in ("0091", "0092"):
        (refined_dir / f"{tid}.md").write_text(
            f"---\nid: '{tid}'\ntitle: Task {tid}\nstatus: Refined\n---\n# Task\n",
            encoding="utf-8",
        )
    (backlog_dir / "PRIORITY.md").write_text(
        "1. **TASK-0091 (Refined)**: [0091.md](refined/0091.md)\n"
        "2. **TASK-0092 (Refined)**: [0092.md](refined/0092.md)\n"
    )

    executed_tasks = []

    def mock_pipeline(task, repo_root, queue, local_mode=False, skip_agent=False):
        executed_tasks.append(task.id)
        return TaskExecutionResult(task, True, "Completed")

    monkeypatch.setattr("tools.backlog_engine.orchestrator.execute_task_pipeline", mock_pipeline)

    exit_code = run_orchestrator(repo_root=tmp_path, drain=False, concurrency=2, local_mode=True)
    assert exit_code == 0
    assert sorted(executed_tasks) == ["0091", "0092"]
