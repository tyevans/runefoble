"""Frontdoor tests for PR merge conflict detection, automated agent repair, and PR failure teardown."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.backlog_engine import ci_watcher, orchestrator
from tools.backlog_engine.models import Task, TaskStatus
from tools.backlog_engine.orchestrator import execute_task_pipeline
from tools.backlog_engine.queue import BacklogQueue


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

    patches = {
        "create_worktree": lambda *a, **k: tmp_path / "worktree",
        "run_preflight_checks": lambda *a, **k: (True, "Passed"),
        "commit_and_push": lambda *a, **k: None,
        "create_pull_request": lambda *a, **k: "https://github.com/example/pr/7",
        "wait_for_ci_checks": lambda *a, **k: False,
        "close_pull_request": lambda wt, url, reason: closed_prs.append((url, reason)),
        "cleanup_worktree": lambda *a, **k: None,
    }
    for name, fn in patches.items():
        monkeypatch.setattr(f"tools.backlog_engine.orchestrator.{name}", fn)

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


def test_watch_and_repair_pull_request_heals_ci_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that watch_and_repair_pull_request invokes agent repair on CI failure and succeeds on retry."""
    task = Task(
        id="0082", title="OpenPanel", status=TaskStatus.REVIEW, file_path=tmp_path / "82.md"
    )
    agent_prompts = []
    pushed = []
    poll_count = 0

    def mock_wait(wt, pr_url, *a, **k):
        nonlocal poll_count
        poll_count += 1
        return poll_count > 1  # False on first call (CI failure), True on second call (repaired)

    monkeypatch.setattr(orchestrator, "wait_for_ci_checks", mock_wait)
    monkeypatch.setattr(
        orchestrator,
        "get_ci_failure_diagnostics",
        lambda wt, url: ("ci_failed", "Test failure in analytics.py"),
    )
    monkeypatch.setattr(orchestrator, "sync_and_resolve_base_ref", lambda *a, **k: (True, "synced"))
    monkeypatch.setattr(
        orchestrator,
        "run_agent_in_worktree",
        lambda wt, t, custom_prompt=None, **k: (
            agent_prompts.append(custom_prompt) or (True, "fixed")
        ),
    )
    monkeypatch.setattr(orchestrator, "run_preflight_checks", lambda wt: (True, "preflight ok"))
    monkeypatch.setattr(orchestrator, "commit_and_push", lambda wt, t, b: pushed.append(b))

    success = orchestrator.watch_and_repair_pull_request(
        tmp_path, task, "feat/0082-openpanel", "https://github.com/example/pr/36", "worker-0082"
    )
    assert success is True
    assert poll_count == 2
    assert len(agent_prompts) == 1
    assert "Test failure in analytics.py" in agent_prompts[0]
    assert pushed == ["feat/0082-openpanel"]


def test_watch_and_repair_pull_request_heals_merge_conflict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that watch_and_repair_pull_request handles mid-flight merge conflicts on PR."""
    task = Task(
        id="0074", title="Theme Contrast", status=TaskStatus.REVIEW, file_path=tmp_path / "74.md"
    )
    poll_count = 0
    sync_called = []

    def mock_wait(wt, pr_url, *a, **k):
        nonlocal poll_count
        poll_count += 1
        return poll_count > 1

    monkeypatch.setattr(orchestrator, "wait_for_ci_checks", mock_wait)
    monkeypatch.setattr(
        orchestrator,
        "get_ci_failure_diagnostics",
        lambda wt, url: ("conflict", "PR has merge conflicts with base branch"),
    )
    monkeypatch.setattr(
        orchestrator,
        "sync_and_resolve_base_ref",
        lambda wt, t, **k: sync_called.append(t.id) or (True, "conflict resolved"),
    )
    monkeypatch.setattr(orchestrator, "run_preflight_checks", lambda wt: (True, "preflight ok"))
    monkeypatch.setattr(orchestrator, "commit_and_push", lambda wt, t, b: None)

    success = orchestrator.watch_and_repair_pull_request(
        tmp_path, task, "feat/0074-theme", "https://github.com/example/pr/37", "worker-0074"
    )
    assert success is True
    assert poll_count == 2
    assert len(sync_called) == 1
