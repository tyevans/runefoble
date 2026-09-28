"""Blackbox tests for Backlog Engine CLI frontdoor commands (list, status, claim, complete)."""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Executes backlog CLI via python -m entrypoint in specified directory."""
    cmd = [sys.executable, "-m", "tools.backlog_engine.cli", *args]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def test_cli_list_ready_and_all(mock_backlog_repo: Path):
    """Verifies 'list' lists only ready unblocked tasks by default, and --all lists everything."""
    res_ready = run_cli("list", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo)
    assert res_ready.returncode == 0
    assert "Ready Unblocked Tasks (1 found):" in res_ready.stdout
    assert "TASK-0002" in res_ready.stdout
    assert "TASK-0003" not in res_ready.stdout

    res_all = run_cli("list", "--all", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo)
    assert res_all.returncode == 0
    assert "All Backlog Tasks (4 found):" in res_all.stdout
    assert "TASK-0001" in res_all.stdout
    assert "TASK-0002" in res_all.stdout
    assert "TASK-0003" in res_all.stdout
    assert "TASK-0004" in res_all.stdout


def test_cli_status(mock_backlog_repo: Path):
    """Verifies 'status' displays aggregated counts across all lifecycle states."""
    res = run_cli("status", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo)
    assert res.returncode == 0
    assert "Backlog Engine Status:" in res.stdout
    assert "Total tasks:           4" in res.stdout
    assert "Ready (unblocked):     1" in res.stdout
    assert "Complete" in res.stdout
    assert "Proposed" in res.stdout


def test_cli_claim_lifecycle(mock_backlog_repo: Path):
    """Verifies 'claim' sets claimed_by and branch in frontmatter and updates list output."""
    res = run_cli(
        "claim",
        "TASK-0002",
        "--worker-id",
        "worker-alpha",
        "--branch",
        "feat/alpha-0002",
        "--repo-dir",
        str(mock_backlog_repo),
        cwd=mock_backlog_repo,
    )
    assert res.returncode == 0
    assert "Claimed TASK-0002 for worker 'worker-alpha'" in res.stdout

    # Verify task file was updated on disk
    t2_file = mock_backlog_repo / "docs" / "project" / "backlog" / "refined" / "0002-task.md"
    content = t2_file.read_text(encoding="utf-8")
    assert "claimed_by: worker-alpha" in content
    assert "branch: feat/alpha-0002" in content

    # Now no ready unblocked tasks remain
    res_list = run_cli("list", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo)
    assert "Ready Unblocked Tasks (0 found):" in res_list.stdout


def test_cli_complete_lifecycle(mock_backlog_repo: Path):
    """Verifies 'complete' moves task to complete/, updates PRIORITY.md, and creates git commit."""
    res = run_cli(
        "complete",
        "TASK-0002",
        "--repo-dir",
        str(mock_backlog_repo),
        cwd=mock_backlog_repo,
    )
    assert res.returncode == 0
    assert "Completed TASK-0002" in res.stdout

    # Verify file moved to complete/
    t2_dest = mock_backlog_repo / "docs" / "project" / "backlog" / "complete" / "0002-task.md"
    assert t2_dest.exists()
    t2_old = mock_backlog_repo / "docs" / "project" / "backlog" / "refined" / "0002-task.md"
    assert not t2_old.exists()

    # Verify PRIORITY.md was updated to Complete
    priority_text = (mock_backlog_repo / "docs" / "project" / "backlog" / "PRIORITY.md").read_text(
        encoding="utf-8"
    )
    assert "TASK-0002 (Complete)" in priority_text

    # Verify git commit was created
    git_log = subprocess.run(
        ["git", "log", "-n", "1", "--oneline"],
        cwd=mock_backlog_repo,
        capture_output=True,
        text=True,
    )
    assert "chore(backlog): complete TASK-0002" in git_log.stdout

    # Now TASK-0003 should be unblocked and ready!
    res_list = run_cli("list", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo)
    assert "Ready Unblocked Tasks (1 found):" in res_list.stdout
    assert "TASK-0003" in res_list.stdout


def test_cli_error_handling_for_unknown_tasks(mock_backlog_repo: Path):
    """Verifies that claiming or completing unknown task IDs fails gracefully."""
    res_claim = run_cli(
        "claim", "TASK-9999", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo
    )
    assert res_claim.returncode == 1
    assert "Task TASK-9999 not found" in res_claim.stdout

    res_comp = run_cli(
        "complete", "TASK-9999", "--repo-dir", str(mock_backlog_repo), cwd=mock_backlog_repo
    )
    assert res_comp.returncode == 1
    assert "Task TASK-9999 not found" in res_comp.stdout
