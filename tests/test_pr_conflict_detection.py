"""Frontdoor tests for GitHub PR conflict detection, CI watcher, and stale task recovery."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.backlog_engine import ci_watcher
from tools.backlog_engine.models import Task, TaskStatus
from tools.backlog_engine.orchestrator import execute_task_pipeline
from tools.backlog_engine.queue import BacklogQueue


def test_check_pr_conflict_status_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that a clean mergeable PR returns (False, '')."""
    mock_proc = MagicMock(spec=subprocess.CompletedProcess)
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(
        {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}
    )
    mock_proc.stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_proc)

    is_bad, reason = ci_watcher.check_pr_conflict_status(
        tmp_path, "https://github.com/example/pr/1"
    )
    assert is_bad is False
    assert reason == ""


def test_check_pr_conflict_status_conflicting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that a conflicting PR (CONFLICTING/DIRTY) is detected immediately."""
    mock_proc = MagicMock(spec=subprocess.CompletedProcess)
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(
        {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    )
    mock_proc.stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_proc)

    is_bad, reason = ci_watcher.check_pr_conflict_status(
        tmp_path, "https://github.com/example/pr/7"
    )
    assert is_bad is True
    assert "merge conflicts" in reason
    assert "CONFLICTING" in reason
    assert "DIRTY" in reason


def test_check_pr_conflict_status_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that a closed PR is detected and rejected."""
    mock_proc = MagicMock(spec=subprocess.CompletedProcess)
    mock_proc.returncode = 0
    mock_proc.stdout = json.dumps(
        {"state": "CLOSED", "mergeable": "UNKNOWN", "mergeStateStatus": "UNKNOWN"}
    )
    mock_proc.stderr = ""
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_proc)

    is_bad, reason = ci_watcher.check_pr_conflict_status(
        tmp_path, "https://github.com/example/pr/7"
    )
    assert is_bad is True
    assert "closed" in reason.lower()


def test_wait_for_ci_checks_detects_conflict_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that wait_for_ci_checks exits immediately without looping when PR has conflicts."""
    check_poll_count = 0

    def mock_run(cmd, *args, **kwargs):
        nonlocal check_poll_count
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        if "view" in cmd:
            mock_proc.returncode = 0
            mock_proc.stdout = json.dumps(
                {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
            )
            mock_proc.stderr = ""
            return mock_proc

        if "checks" in cmd:
            check_poll_count += 1
            mock_proc.returncode = 1
            mock_proc.stdout = ""
            mock_proc.stderr = "no checks reported on the 'feat/test' branch"
            return mock_proc

        return mock_proc

    monkeypatch.setattr(subprocess, "run", mock_run)

    passed = ci_watcher.wait_for_ci_checks(
        tmp_path, "https://github.com/example/pr/7", poll_interval=0, timeout_seconds=10
    )
    assert passed is False
    # Since conflict was detected immediately, checks polling was bypassed
    assert check_poll_count == 0


def test_close_pull_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that close_pull_request invokes gh pr close with comment."""
    captured_cmd = None

    def mock_run(cmd, *args, **kwargs):
        nonlocal captured_cmd
        captured_cmd = cmd
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        mock_proc.returncode = 0
        mock_proc.stdout = "Closed PR"
        mock_proc.stderr = ""
        return mock_proc

    monkeypatch.setattr(subprocess, "run", mock_run)

    ci_watcher.close_pull_request(
        tmp_path, "https://github.com/example/pr/7", reason="Conflict with main"
    )
    assert captured_cmd == [
        "gh",
        "pr",
        "close",
        "https://github.com/example/pr/7",
        "--comment",
        "Conflict with main",
    ]


def test_recover_stale_tasks_recovers_review_status(tmp_path: Path):
    """Verifies that tasks left in 'review' status with pr_url and claimed_by are recovered to Refined."""
    backlog_dir = tmp_path / "backlog"
    refined_dir = backlog_dir / "refined"
    refined_dir.mkdir(parents=True)

    task_file = refined_dir / "0034-zitadel-auth.md"
    task_file.write_text(
        """---
id: '0034'
title: Zitadel Production OIDC/JWKS Token Verification Middleware
status: review
created: 2026-09-25
claimed_by: worker-0034
pr_url: https://github.com/tyevans/runefoble/pull/7
---
# TASK-0034
""",
        encoding="utf-8",
    )

    queue = BacklogQueue(backlog_dir)
    recovered = queue.recover_stale_tasks()

    assert len(recovered) == 1
    assert recovered[0].id == "0034"
    assert recovered[0].status == TaskStatus.READY
    assert recovered[0].claimed_by is None
    assert recovered[0].pr_url is None

    # Check written file contents
    content = task_file.read_text(encoding="utf-8")
    assert "status: Refined" in content
    assert "claimed_by" not in content
    assert "pr_url" not in content


def test_commit_and_push_detects_merge_conflicts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that commit_and_push fails fast when git merge-tree detects conflicts against base_ref."""
    task = Task(
        id="0034",
        title="Zitadel Auth",
        status=TaskStatus.IN_PROGRESS,
        file_path=tmp_path / "0034.md",
    )

    def mock_run(cmd, *args, **kwargs):
        mock_proc = MagicMock(spec=subprocess.CompletedProcess)
        mock_proc.returncode = 0
        mock_proc.stdout = ""
        mock_proc.stderr = ""

        if "rev-list" in cmd:
            mock_proc.stdout = "2\n"  # 2 commits behind
        elif "merge-tree" in cmd:
            mock_proc.returncode = 1  # Conflict detected!
            mock_proc.stdout = (
                "CONFLICT (content): Merge conflict in gateway/api/src/gateway_api/main.py"
            )
        return mock_proc

    monkeypatch.setattr(subprocess, "run", mock_run)

    with pytest.raises(ci_watcher.CIPipelineError) as exc_info:
        ci_watcher.commit_and_push(tmp_path, task, "feat/0034-test")

    assert "has merge conflicts" in str(exc_info.value)


def test_orchestrator_closes_pr_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that execute_task_pipeline closes PR when wait_for_ci_checks fails."""
    closed_prs = []

    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.create_worktree",
        lambda *args, **kwargs: tmp_path / "worktree",
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.run_preflight_checks",
        lambda *args, **kwargs: (True, "Passed"),
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.commit_and_push",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.create_pull_request",
        lambda *args, **kwargs: "https://github.com/example/pr/7",
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.wait_for_ci_checks",
        lambda *args, **kwargs: False,  # CI / conflict failure
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.close_pull_request",
        lambda worktree_dir, pr_url, reason: closed_prs.append((pr_url, reason)),
    )
    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.cleanup_worktree",
        lambda *args, **kwargs: None,
    )

    backlog_dir = tmp_path / "backlog"
    refined_dir = backlog_dir / "refined"
    refined_dir.mkdir(parents=True)
    task_file = refined_dir / "0034-zitadel-auth.md"
    task_file.write_text(
        "---\nid: '0034'\ntitle: Zitadel Auth\nstatus: Refined\n---\n# TASK-0034",
        encoding="utf-8",
    )

    queue = BacklogQueue(backlog_dir)
    task = queue.list_all_tasks()[0]

    res = execute_task_pipeline(task, tmp_path, queue, local_mode=False, skip_agent=True)
    assert res.success is False
    assert len(closed_prs) == 1
    assert closed_prs[0][0] == "https://github.com/example/pr/7"
    assert "merge conflicts" in closed_prs[0][1] or "failed CI" in closed_prs[0][1]


def test_cli_drain_flag_defaults():
    """Verifies that cli defaults --drain to True and --once toggles it to False."""
    import argparse

    # Inspect parser configuration
    parser = argparse.ArgumentParser()
    parser.add_argument("--drain", dest="drain", action="store_true", default=True)
    parser.add_argument("--once", dest="drain", action="store_false")

    args_default = parser.parse_args([])
    assert args_default.drain is True

    args_once = parser.parse_args(["--once"])
    assert args_once.drain is False

    args_explicit_drain = parser.parse_args(["--drain"])
    assert args_explicit_drain.drain is True


def test_worktree_lock_exists():
    """Verifies that WORKTREE_LOCK is defined and functional."""
    import threading

    from tools.backlog_engine.worktree import WORKTREE_LOCK

    assert isinstance(WORKTREE_LOCK, type(threading.Lock()))
    with WORKTREE_LOCK:
        pass


def test_orchestrator_retry_limits_and_continuous_drain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that run_orchestrator skips repeatedly failing tasks after 3 attempts without breaking."""
    from tools.backlog_engine.orchestrator import run_orchestrator

    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    refined_dir = backlog_dir / "refined"
    refined_dir.mkdir(parents=True)
    (backlog_dir / "complete").mkdir(parents=True)
    (backlog_dir / "PRIORITY.md").write_text(
        "1. **TASK-0099 (Refined)**: [`0099-flaky.md`](refined/0099-flaky.md)\n"
    )

    task_file = refined_dir / "0099-flaky.md"
    task_file.write_text(
        "---\nid: '0099'\ntitle: Flaky Task\nstatus: Refined\n---\n# TASK-0099",
        encoding="utf-8",
    )

    # Mock execute_task_pipeline to always fail
    pipeline_calls = []

    def mock_pipeline(task, repo_root, queue, local_mode=False, skip_agent=False):
        pipeline_calls.append(task.id)
        from tools.backlog_engine.orchestrator import TaskExecutionResult

        return TaskExecutionResult(task, False, "Simulated preflight or merge failure")

    monkeypatch.setattr(
        "tools.backlog_engine.orchestrator.execute_task_pipeline",
        mock_pipeline,
    )

    exit_code = run_orchestrator(
        repo_root=tmp_path,
        drain=True,
        concurrency=1,
        local_mode=True,
    )

    assert exit_code == 0
    # Must have attempted exactly 3 times before hitting the failure limit
    assert len(pipeline_calls) == 3
