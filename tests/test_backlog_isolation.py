"""Tests for Backlog Isolation and Merge Conflict Prevention in Backlog Engine."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.backlog_engine.agent_worker import build_worker_prompt
from tools.backlog_engine.ci_watcher import commit_and_push
from tools.backlog_engine.models import Task, TaskStatus
from tools.backlog_engine.orchestrator import execute_task_pipeline
from tools.backlog_engine.worktree import enforce_backlog_isolation


def test_build_worker_prompt_enforces_backlog_isolation():
    """Verifies that the worker prompt instructs agents never to modify docs/project/backlog/."""
    task = Task(
        id="0045",
        title="Test Task Title",
        status=TaskStatus.READY,
        file_path=Path("docs/project/backlog/refined/0045-test.md"),
        dependencies=["TASK-0001"],
        governing_adrs=["ADR-0001"],
        priority_rank=45,
        body="Task body specification.",
    )
    prompt = build_worker_prompt(task)
    assert "8. Backlog Isolation:" in prompt
    assert "DO NOT edit, rename, or move any files under docs/project/backlog/" in prompt


def test_enforce_backlog_isolation_reverts_uncommitted_edits(tmp_path: Path):
    """Verifies that enforce_backlog_isolation restores docs/project/backlog/ to main."""
    # Initialize a git repo in tmp_path
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    backlog_dir.mkdir(parents=True)
    priority_file = backlog_dir / "PRIORITY.md"
    priority_file.write_text("Original PRIORITY.md\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True
    )

    # Simulate an agent modifying PRIORITY.md in working tree
    priority_file.write_text("Modified PRIORITY.md by rogue agent\n", encoding="utf-8")
    assert priority_file.read_text(encoding="utf-8") == "Modified PRIORITY.md by rogue agent\n"

    # Enforce isolation
    reverted, msg = enforce_backlog_isolation(tmp_path)
    assert reverted is True
    assert "Reverted branch modifications" in msg
    assert priority_file.read_text(encoding="utf-8") == "Original PRIORITY.md\n"


def test_commit_and_push_reverts_backlog_changes_before_staging(tmp_path: Path):
    """Verifies that commit_and_push automatically cleanses docs/project/backlog/ changes."""
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    backlog_dir.mkdir(parents=True)
    priority_file = backlog_dir / "PRIORITY.md"
    priority_file.write_text("Original PRIORITY.md\n", encoding="utf-8")

    code_file = tmp_path / "service.py"
    code_file.write_text("def run(): pass\n", encoding="utf-8")

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True, capture_output=True
    )

    # Create feature branch
    subprocess.run(
        ["git", "checkout", "-b", "feat/0045-test"], cwd=tmp_path, check=True, capture_output=True
    )

    # Rogue edits to backlog and valid edits to service
    priority_file.write_text("Corrupted PRIORITY.md\n", encoding="utf-8")
    code_file.write_text("def run(): return 42\n", encoding="utf-8")

    task = Task(
        id="0045",
        title="Test Feature",
        status=TaskStatus.READY,
        file_path=Path("docs/project/backlog/refined/0045-test.md"),
        dependencies=[],
        governing_adrs=[],
        priority_rank=45,
        body="Body",
    )

    # Mock git push so it doesn't fail trying to talk to origin
    with patch("tools.backlog_engine.ci_watcher.run_cmd") as mock_cmd:
        # Allow actual subprocess calls except push
        def side_effect(cmd, cwd, check=False):
            if "push" in cmd:
                res = MagicMock()
                res.returncode = 0
                return res
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)

        mock_cmd.side_effect = side_effect
        commit_and_push(tmp_path, task, "feat/0045-test")

    # PRIORITY.md should have been reverted to original
    assert priority_file.read_text(encoding="utf-8") == "Original PRIORITY.md\n"
    # Service file should have new code
    assert "return 42" in code_file.read_text(encoding="utf-8")


def test_orchestrator_parallel_dispatch_does_not_hold_merge_lock_during_ci(tmp_path: Path):
    """Verifies that commit_and_push, PR creation, and CI waiting run outside MERGE_LOCK."""
    from tools.backlog_engine import orchestrator

    task = Task(
        id="0045",
        title="Test Feature",
        status=TaskStatus.READY,
        file_path=tmp_path / "docs" / "project" / "backlog" / "refined" / "0045-test.md",
        dependencies=[],
        governing_adrs=[],
        priority_rank=45,
        body="Body",
    )

    mock_queue = MagicMock()
    mock_queue.complete_task.return_value = (
        tmp_path / "docs" / "project" / "backlog" / "complete" / "0045-test.md"
    )

    lock_held_during_ci = None

    def mock_wait_ci(worktree, pr_url):
        nonlocal lock_held_during_ci
        lock_held_during_ci = orchestrator.MERGE_LOCK.locked()
        return True

    with (
        patch("tools.backlog_engine.orchestrator.create_worktree", return_value=tmp_path),
        patch("tools.backlog_engine.orchestrator.run_preflight_checks", return_value=(True, "")),
        patch("tools.backlog_engine.orchestrator.commit_and_push"),
        patch(
            "tools.backlog_engine.orchestrator.create_pull_request",
            return_value="https://github.com/pr/1",
        ),
        patch(
            "tools.backlog_engine.orchestrator.wait_for_ci_checks",
            side_effect=mock_wait_ci,
        ),
        patch("tools.backlog_engine.orchestrator.merge_pull_request"),
        patch("tools.backlog_engine.orchestrator.run_git") as mock_git,
        patch("tools.backlog_engine.orchestrator.cleanup_worktree"),
    ):
        mock_git.return_value = MagicMock(returncode=0, stdout="")
        res = execute_task_pipeline(
            task,
            tmp_path,
            mock_queue,
            local_mode=False,
            skip_agent=True,
        )

    assert res.success is True
    # The crucial assertion: MERGE_LOCK was NOT held while waiting for CI checks!
    assert lock_held_during_ci is False
