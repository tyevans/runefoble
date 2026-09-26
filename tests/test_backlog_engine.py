"""Tests for autonomous backlog execution engine."""

from pathlib import Path

import pytest

from tools.backlog_engine.models import TaskStatus
from tools.backlog_engine.queue import BacklogQueue, parse_task_file


@pytest.fixture
def temp_backlog_dir(tmp_path: Path):
    """Creates a temporary backlog directory structure for isolated testing."""
    backlog = tmp_path / "docs" / "project" / "backlog"
    (backlog / "complete").mkdir(parents=True)
    (backlog / "refined").mkdir(parents=True)
    (backlog / "proposed").mkdir(parents=True)

    # Priority file
    priority_content = """# Backlog Priority Index
1. **TASK-0001 (Complete)**: [`0001-task.md`](complete/0001-task.md)
2. **TASK-0002 (Refined)**: [`0002-task.md`](refined/0002-task.md)
3. **TASK-0003 (Refined)**: [`0003-task.md`](refined/0003-task.md)
"""
    (backlog / "PRIORITY.md").write_text(priority_content, encoding="utf-8")
    return backlog


def test_parse_task_file_octal_safety(temp_backlog_dir: Path):
    """Ensures leading-zero task IDs are not parsed as octal integers."""
    task_file = temp_backlog_dir / "refined" / "0024-sample-task.md"
    content = """---
id: 0024
title: Sample Octal Safety Task
status: Refined
dependencies: [TASK-0001]
governing_adrs: [ADR-0001]
---

# TASK-0024: Sample Octal Safety Task
Description here.
"""
    task_file.write_text(content, encoding="utf-8")

    task = parse_task_file(task_file, priority_rank=1)
    assert task.id == "0024"
    assert task.canonical_id == "TASK-0024"
    assert task.status == TaskStatus.READY
    assert task.dependencies == ["TASK-0001"]


def test_dependency_resolution_blocks_and_unblocks(temp_backlog_dir: Path):
    """Verifies that tasks with unmet dependencies are blocked, while satisfied ones are ready."""
    # Completed task: TASK-0001
    t1_file = temp_backlog_dir / "complete" / "0001-task.md"
    t1_file.write_text(
        "---\nid: 0001\ntitle: Task 1\nstatus: Complete\n---\nBody",
        encoding="utf-8",
    )

    # Refined task 2: depends on TASK-0001 (satisfied)
    t2_file = temp_backlog_dir / "refined" / "0002-task.md"
    t2_file.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: Refined\ndependencies: [TASK-0001]\n---\nBody",
        encoding="utf-8",
    )

    # Refined task 3: depends on TASK-0002 (unsatisfied)
    t3_file = temp_backlog_dir / "refined" / "0003-task.md"
    t3_file.write_text(
        "---\nid: 0003\ntitle: Task 3\nstatus: Refined\ndependencies: [TASK-0002]\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)
    ready = queue.get_ready_unblocked_tasks()

    # Only Task 2 should be ready; Task 3 is blocked by Task 2
    assert len(ready) == 1
    assert ready[0].canonical_id == "TASK-0002"


def test_task_claiming_lifecycle(temp_backlog_dir: Path):
    """Verifies atomic state transitions: claim -> review -> complete."""
    t2_file = temp_backlog_dir / "refined" / "0002-task.md"
    t2_file.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: Refined\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)
    tasks = queue.get_ready_unblocked_tasks()
    assert len(tasks) == 1
    task = tasks[0]

    # Claim
    queue.claim_task(task, worker_id="worker-test", branch="feat/0002-task")
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.claimed_by == "worker-test"

    # Once claimed, it is excluded from ready queue
    assert len(queue.get_ready_unblocked_tasks()) == 0

    # Mark Review
    queue.mark_review(task, pr_url="https://github.com/example/pr/1")
    assert task.status == TaskStatus.REVIEW
    assert task.pr_url == "https://github.com/example/pr/1"

    # Complete
    new_path = queue.complete_task(task)
    assert task.status == TaskStatus.COMPLETE
    assert new_path.parent.name == "complete"
    assert not t2_file.exists()
    assert new_path.exists()

    # PRIORITY.md should be updated
    priority_text = (temp_backlog_dir / "PRIORITY.md").read_text(encoding="utf-8")
    assert "**TASK-0002 (Complete)**" in priority_text
    assert "(complete/0002-task.md)" in priority_text


def test_build_repair_prompt():
    """Verifies that the repair prompt includes the error log and clear invariant guidance."""
    from tools.backlog_engine.agent_worker import build_repair_prompt
    from tools.backlog_engine.models import Task, TaskStatus

    dummy_task = Task(
        id="0024",
        title="SpiceDB Sync",
        status=TaskStatus.READY,
        file_path=Path("/dummy/path.md"),
    )
    error_log = (
        "❌ Pre-flight check 'Ruff Format' failed (exit code 1):\nunformatted: docs/how-to.md"
    )

    prompt = build_repair_prompt(dummy_task, error_log)
    assert "TASK-0024" in prompt
    assert "SpiceDB Sync" in prompt
    assert "PRE-FLIGHT VERIFICATION LOG" in prompt
    assert "unformatted: docs/how-to.md" in prompt
    assert "uv run ruff format ." in prompt
    assert "uv run ruff check ." in prompt
    assert "uv run pytest" in prompt


def test_preflight_checks_aggregates_multiple_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that run_preflight_checks collects multiple failures instead of exiting on first."""
    import subprocess

    from tools.backlog_engine.worktree import run_preflight_checks

    def mock_subprocess_run(cmd, *args, **kwargs):
        if "check" in cmd:
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="Lint violation E501", stderr=""
            )
        elif "format" in cmd:
            return subprocess.CompletedProcess(
                cmd, returncode=1, stdout="File unformatted", stderr=""
            )
        elif "pytest" in cmd:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="All passed", stderr="")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    passed, log = run_preflight_checks(tmp_path)
    assert passed is False
    assert "Pre-flight check 'Ruff Lint' failed" in log
    assert "Lint violation E501" in log
    assert "Pre-flight check 'Ruff Format' failed" in log
    assert "File unformatted" in log
    assert "Pytest Suite passed" in log


def test_orchestrator_repair_loop_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that the orchestrator retries preflight with agent feedback and succeeds."""
    from unittest.mock import MagicMock

    from tools.backlog_engine import orchestrator
    from tools.backlog_engine.models import Task, TaskStatus

    # Create dummy task
    task = Task(
        id="0099",
        title="Repairable Task",
        status=TaskStatus.READY,
        file_path=tmp_path / "0099-task.md",
    )

    mock_queue = MagicMock()
    mock_create_worktree = MagicMock(return_value=tmp_path / "worktree")
    mock_cleanup = MagicMock()
    mock_merge_local = MagicMock()

    # Preflight fails on first check, passes on second check after repair
    preflight_call_count = 0

    def mock_preflight(wt_dir):
        nonlocal preflight_call_count
        preflight_call_count += 1
        if preflight_call_count == 1:
            return False, "❌ Ruff Format failed: file needs formatting"
        return True, "✅ All checks passed"

    agent_calls = []

    def mock_agent_run(wt_dir, t, feedback=None):
        agent_calls.append({"feedback": feedback})
        return True, "Fixed formatting"

    monkeypatch.setattr(orchestrator, "create_worktree", mock_create_worktree)
    monkeypatch.setattr(orchestrator, "cleanup_worktree", mock_cleanup)
    monkeypatch.setattr(orchestrator, "run_preflight_checks", mock_preflight)
    monkeypatch.setattr(orchestrator, "run_agent_in_worktree", mock_agent_run)
    monkeypatch.setattr(orchestrator, "merge_local_branch", mock_merge_local)

    res = orchestrator.execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True)
    assert res.success is True
    # Initial run + 1 repair run = 2 agent invocations
    assert len(agent_calls) == 2
    assert agent_calls[0]["feedback"] is None
    assert "Ruff Format failed" in agent_calls[1]["feedback"]
    assert preflight_call_count == 2
    mock_queue.complete_task.assert_called_once_with(task)


def test_orchestrator_repair_loop_exhaustion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that if repair attempts fail repeatedly, orchestrator exits cleanly after max attempts."""
    from unittest.mock import MagicMock

    from tools.backlog_engine import orchestrator
    from tools.backlog_engine.models import Task, TaskStatus

    task = Task(
        id="0099",
        title="Unrepairable Task",
        status=TaskStatus.READY,
        file_path=tmp_path / "0099-task.md",
    )

    mock_queue = MagicMock()
    mock_create_worktree = MagicMock(return_value=tmp_path / "worktree")
    mock_cleanup = MagicMock()

    # Preflight always fails
    monkeypatch.setattr(orchestrator, "create_worktree", mock_create_worktree)
    monkeypatch.setattr(orchestrator, "cleanup_worktree", mock_cleanup)
    monkeypatch.setattr(
        orchestrator, "run_preflight_checks", lambda wt: (False, "Persistent Test Failure")
    )
    monkeypatch.setattr(
        orchestrator, "run_agent_in_worktree", lambda wt, t, feedback=None: (True, "Agent done")
    )

    res = orchestrator.execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True)
    assert res.success is False
    assert "Pre-flight checks failed after 3 repair attempt(s)" in res.message
    assert "Persistent Test Failure" in res.message
    mock_queue.complete_task.assert_not_called()
    mock_queue.release_task.assert_called_once_with(task)
    mock_cleanup.assert_called_once()


def test_task_release_lifecycle(temp_backlog_dir: Path):
    """Verifies that release_task cleanly resets frontmatter on disk and re-enables queue readiness."""
    t2_file = temp_backlog_dir / "refined" / "0002-task.md"
    t2_file.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: Refined\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)
    tasks = queue.get_ready_unblocked_tasks()
    assert len(tasks) == 1
    task = tasks[0]

    # Claim task
    queue.claim_task(task, worker_id="worker-release", branch="feat/task-0002")
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.claimed_by == "worker-release"
    assert len(queue.get_ready_unblocked_tasks()) == 0

    # Release task
    queue.release_task(task)
    assert task.status == TaskStatus.READY
    assert task.claimed_by is None
    assert task.branch is None

    # Disk content should reflect removal of claimed_by and branch
    disk_content = t2_file.read_text(encoding="utf-8")
    assert "claimed_by" not in disk_content
    assert "branch" not in disk_content
    assert "status: Refined" in disk_content

    # Now it should be back in the ready queue
    ready_tasks = queue.get_ready_unblocked_tasks()
    assert len(ready_tasks) == 1
    assert ready_tasks[0].canonical_id == "TASK-0002"


def test_recover_stale_tasks(temp_backlog_dir: Path):
    """Verifies that recover_stale_tasks finds and releases orphaned in-progress tasks."""
    # Create two stranded tasks and one normal task in refined/
    t2_file = temp_backlog_dir / "refined" / "0002-task.md"
    t2_file.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: in-progress\nclaimed_by: worker-old\nbranch: feat/old\n---\nBody",
        encoding="utf-8",
    )

    t3_file = temp_backlog_dir / "refined" / "0003-task.md"
    t3_file.write_text(
        "---\nid: 0003\ntitle: Task 3\nstatus: in-progress\nclaimed_by: worker-old2\n---\nBody",
        encoding="utf-8",
    )

    t4_file = temp_backlog_dir / "refined" / "0004-task.md"
    t4_file.write_text(
        "---\nid: 0004\ntitle: Task 4\nstatus: Refined\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)

    # Before recovery, only task 4 is ready
    assert len(queue.get_ready_unblocked_tasks()) == 1

    # Recover stale tasks
    recovered = queue.recover_stale_tasks()
    assert len(recovered) == 2
    recovered_ids = {t.canonical_id for t in recovered}
    assert recovered_ids == {"TASK-0002", "TASK-0003"}

    # All 3 tasks should now be ready
    ready = queue.get_ready_unblocked_tasks()
    assert len(ready) == 3


def test_orchestrator_releases_task_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that execute_task_pipeline catches KeyboardInterrupt and releases the task."""
    from unittest.mock import MagicMock

    from tools.backlog_engine import orchestrator
    from tools.backlog_engine.models import Task, TaskStatus

    task = Task(
        id="0099",
        title="Interrupted Task",
        status=TaskStatus.READY,
        file_path=tmp_path / "0099-task.md",
    )

    mock_queue = MagicMock()
    mock_create_worktree = MagicMock(return_value=tmp_path / "worktree")
    mock_cleanup = MagicMock()

    def mock_agent_interrupt(wt, t, feedback=None):
        raise KeyboardInterrupt()

    monkeypatch.setattr(orchestrator, "create_worktree", mock_create_worktree)
    monkeypatch.setattr(orchestrator, "cleanup_worktree", mock_cleanup)
    monkeypatch.setattr(orchestrator, "run_agent_in_worktree", mock_agent_interrupt)

    with pytest.raises(KeyboardInterrupt):
        orchestrator.execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True)

    mock_queue.claim_task.assert_called_once()
    mock_queue.release_task.assert_called_once_with(task)
    mock_cleanup.assert_called_once()


def test_wait_for_ci_checks_success_after_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that wait_for_ci_checks waits through unregistered and pending checks to success."""
    import json
    import subprocess
    from unittest.mock import MagicMock

    from tools.backlog_engine import ci_watcher

    call_count = 0

    def mock_run(cmd, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        if call_count == 1:
            # Initial poll: no checks registered yet
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "no checks reported on the 'feat/test' branch"
        elif call_count == 2:
            # Second poll: checks in progress
            mock_proc.returncode = 8
            mock_proc.stdout = json.dumps(
                [{"name": "Python Lint", "state": "IN_PROGRESS", "bucket": "pending"}]
            )
            mock_proc.stderr = ""
        else:
            # Third poll: all passed
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps(
                [{"name": "Python Lint", "state": "SUCCESS", "bucket": "pass"}]
            )
            mock_proc.stderr = ""
        return mock_proc

    monkeypatch.setattr(subprocess, "run", mock_run)

    passed = ci_watcher.wait_for_ci_checks(
        tmp_path, "https://github.com/example/pr/1", poll_interval=0, timeout_seconds=10
    )
    assert passed is True
    assert call_count == 3


def test_wait_for_ci_checks_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that wait_for_ci_checks detects failed check runs."""
    import json
    import subprocess
    from unittest.mock import MagicMock

    from tools.backlog_engine import ci_watcher

    mock_proc = MagicMock(spec=subprocess.CompletedProcess)
    mock_proc.returncode = 1
    mock_proc.stdout = json.dumps(
        [
            {
                "name": "Python Lint",
                "state": "FAILURE",
                "bucket": "fail",
                "link": "https://example.com/log",
            }
        ]
    )
    mock_proc.stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_proc)

    passed = ci_watcher.wait_for_ci_checks(
        tmp_path, "https://github.com/example/pr/1", poll_interval=0, timeout_seconds=10
    )
    assert passed is False


def test_wait_for_ci_checks_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that wait_for_ci_checks times out cleanly if checks remain pending."""
    import subprocess
    from unittest.mock import MagicMock

    from tools.backlog_engine import ci_watcher

    mock_proc = MagicMock(spec=subprocess.CompletedProcess)
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "no checks reported"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_proc)

    passed = ci_watcher.wait_for_ci_checks(
        tmp_path, "https://github.com/example/pr/1", poll_interval=0.01, timeout_seconds=0.03
    )
    assert passed is False
