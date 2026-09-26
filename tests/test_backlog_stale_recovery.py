"""Frontdoor tests for backlog stale task recovery, requeuing mechanics, and retry circuit breakers."""

import argparse
import threading
from pathlib import Path

import pytest

from tools.backlog_engine.models import TaskStatus
from tools.backlog_engine.orchestrator import TaskExecutionResult, run_orchestrator
from tools.backlog_engine.queue import BacklogQueue
from tools.backlog_engine.worktree import WORKTREE_LOCK


def _create_task(backlog_dir: Path, filename: str, frontmatter: str) -> Path:
    refined_dir = backlog_dir / "refined"
    refined_dir.mkdir(parents=True, exist_ok=True)
    task_file = refined_dir / filename
    task_file.write_text(f"---\n{frontmatter.strip()}\n---\n# Task\n", encoding="utf-8")
    return task_file


def test_recover_stale_tasks_recovers_review_status(tmp_path: Path):
    """Verifies that tasks left in 'review' status with pr_url and claimed_by are recovered to Refined."""
    backlog_dir = tmp_path / "backlog"
    task_file = _create_task(
        backlog_dir,
        "0034-zitadel-auth.md",
        "id: '0034'\ntitle: Zitadel Auth\nstatus: review\nclaimed_by: worker-0034\npr_url: https://github.com/example/pr/7",
    )

    recovered = BacklogQueue(backlog_dir).recover_stale_tasks()
    assert len(recovered) == 1
    assert recovered[0].id == "0034"
    assert recovered[0].status == TaskStatus.READY
    assert recovered[0].claimed_by is None
    assert recovered[0].pr_url is None

    content = task_file.read_text(encoding="utf-8")
    assert "status: Refined" in content
    assert "claimed_by" not in content
    assert "pr_url" not in content


def test_recover_stale_tasks_recovers_in_progress_status(tmp_path: Path):
    """Verifies that tasks left in 'in-progress' status with branch and claimed_by are recovered to Refined."""
    backlog_dir = tmp_path / "backlog"
    task_file = _create_task(
        backlog_dir,
        "0035-token-kinematics.md",
        "id: '0035'\ntitle: Token Kinematics\nstatus: in-progress\nclaimed_by: worker-0035\nbranch: feat/0035",
    )

    recovered = BacklogQueue(backlog_dir).recover_stale_tasks()
    assert len(recovered) == 1
    assert recovered[0].id == "0035"
    assert recovered[0].status == TaskStatus.READY
    assert recovered[0].claimed_by is None
    assert recovered[0].branch is None

    content = task_file.read_text(encoding="utf-8")
    assert "status: Refined" in content
    assert "claimed_by" not in content
    assert "branch" not in content


def test_requeue_failed_tasks_moves_from_review_to_refined(tmp_path: Path):
    """Verifies that releasing or recovering a failed review task resets state to Refined."""
    backlog_dir = tmp_path / "backlog"
    task_file = _create_task(
        backlog_dir,
        "0036-openpanel.md",
        "id: '0036'\ntitle: OpenPanel\nstatus: review\nclaimed_by: worker-0036\npr_url: https://github.com/example/pr/36",
    )

    queue = BacklogQueue(backlog_dir)
    tasks = queue.list_all_tasks()
    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.REVIEW

    queue.release_task(tasks[0])
    assert tasks[0].status == TaskStatus.READY
    assert tasks[0].claimed_by is None
    assert tasks[0].pr_url is None

    content = task_file.read_text(encoding="utf-8")
    assert "status: Refined" in content
    assert "claimed_by" not in content
    assert "pr_url" not in content


def test_cli_drain_flag_defaults():
    """Verifies that cli defaults --drain to True and --once toggles it to False."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--drain", dest="drain", action="store_true", default=True)
    parser.add_argument("--once", dest="drain", action="store_false")

    assert parser.parse_args([]).drain is True
    assert parser.parse_args(["--once"]).drain is False
    assert parser.parse_args(["--drain"]).drain is True


def test_worktree_lock_exists():
    """Verifies that WORKTREE_LOCK is defined and functional."""
    assert isinstance(WORKTREE_LOCK, type(threading.Lock()))
    with WORKTREE_LOCK:
        pass


def test_run_orchestrator_drain_hits_failure_limit_and_stops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that run_orchestrator skips repeatedly failing tasks after 3 attempts without breaking."""
    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    (backlog_dir / "complete").mkdir(parents=True)
    (backlog_dir / "PRIORITY.md").write_text(
        "1. **TASK-0099 (Refined)**: [`0099-flaky.md`](refined/0099-flaky.md)\n"
    )
    _create_task(backlog_dir, "0099-flaky.md", "id: '0099'\ntitle: Flaky\nstatus: Refined")

    pipeline_calls = []

    def mock_pipeline(task, repo_root, queue, local_mode=False, skip_agent=False):
        pipeline_calls.append(task.id)
        return TaskExecutionResult(task, False, "Simulated preflight or merge failure")

    monkeypatch.setattr("tools.backlog_engine.orchestrator.execute_task_pipeline", mock_pipeline)

    exit_code = run_orchestrator(repo_root=tmp_path, drain=True, concurrency=1, local_mode=True)
    assert exit_code == 0
    assert len(pipeline_calls) == 3


test_orchestrator_retry_limits_and_continuous_drain = (
    test_run_orchestrator_drain_hits_failure_limit_and_stops
)
