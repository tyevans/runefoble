"""Tests for scripts/cleanup_worktrees.py git worktree maintenance tool."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from scripts.cleanup_worktrees import (
    CleanupOptions,
    WorktreeInfo,
    decide,
    find_active_pids_for_path,
    is_branch_merged,
    parse_worktrees,
)

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "cleanup_worktrees.py"


def test_parse_worktrees_empty():
    with patch("scripts.cleanup_worktrees.run_cmd") as mock_cmd:
        mock_cmd.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        result = parse_worktrees(Path("/mock/repo"))
        assert result == []


def test_parse_worktrees_multiple():
    sample_output = """worktree /mock/repo
HEAD abc1234
branch refs/heads/main

worktree /mock/repo/.worktrees/task-0001
HEAD def5678
branch refs/heads/feat/task-0001

worktree /mock/repo/.worktrees/detached-one
HEAD 987fedc
detached
"""
    with patch("scripts.cleanup_worktrees.run_cmd") as mock_cmd:
        mock_cmd.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=sample_output
        )
        worktrees = parse_worktrees(Path("/mock/repo"))
        assert len(worktrees) == 3

        # Main worktree
        assert worktrees[0].path == Path("/mock/repo").resolve()
        assert worktrees[0].branch == "main"
        assert worktrees[0].is_main is True

        # Feature worktree
        assert worktrees[1].path == Path("/mock/repo/.worktrees/task-0001").resolve()
        assert worktrees[1].branch == "feat/task-0001"
        assert worktrees[1].is_main is False

        # Detached worktree
        assert worktrees[2].branch is None
        assert worktrees[2].is_main is False


def test_is_branch_merged_direct_ancestor():
    repo_root = Path("/mock/repo")
    with patch("scripts.cleanup_worktrees.run_cmd") as mock_cmd:
        # rev-parse returns 0, merge-base returns 0
        mock_cmd.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="origin/main\n"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
        ]
        merged, reason = is_branch_merged(repo_root, "feat/task-1", "abc123")
        assert merged is True
        assert "Ancestor of" in reason


def test_is_branch_merged_squash():
    repo_root = Path("/mock/repo")
    with patch("scripts.cleanup_worktrees.run_cmd") as mock_cmd:
        # rev-parse origin/main fails, rev-parse main fails, check origin/main for cherry fails,
        # fallback to rev-parse for cherry succeeds, cherry returns squash lines (-)
        mock_cmd.side_effect = [
            # ancestor check origin/main fails
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout=""),
            # ancestor check main fails
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout=""),
            # cherry-pick check
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="- abcdef123\n- 4567890\n"),
        ]
        merged, reason = is_branch_merged(repo_root, "feat/task-1", "abc123")
        assert merged is True
        assert "Squash-merged" in reason


def test_is_branch_unmerged():
    repo_root = Path("/mock/repo")
    with (
        patch("scripts.cleanup_worktrees.run_cmd") as mock_cmd,
        patch("shutil.which", return_value=None),
    ):
        mock_cmd.side_effect = [
            # ancestor check origin/main fails
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout=""),
            # ancestor check main fails
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
            subprocess.CompletedProcess(args=[], returncode=1, stdout=""),
            # cherry-pick check
            subprocess.CompletedProcess(args=[], returncode=0, stdout=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="+ abcdef123\n"),
        ]
        merged, reason = is_branch_merged(repo_root, "feat/task-1", "abc123")
        assert merged is False
        assert reason == "Unmerged"


def test_find_active_pids_for_path_reads_cwd_links(tmp_path: Path):
    target = tmp_path / "worktree"
    (target / "subdir").mkdir(parents=True)
    proc_dir = tmp_path / "proc"
    for pid, cwd in (("12345", target / "subdir"), ("99999", tmp_path)):
        (proc_dir / pid).mkdir(parents=True)
        (proc_dir / pid / "cwd").symlink_to(cwd)
    (proc_dir / "self").mkdir()

    assert find_active_pids_for_path(target, proc_dir) == [12345]


def test_find_active_pids_for_path_cannot_verify_without_proc(tmp_path: Path):
    assert find_active_pids_for_path(tmp_path, tmp_path / "no-proc") is None


def _worktree(**overrides: object) -> WorktreeInfo:
    fields: dict[str, object] = {
        "path": Path("/repo/.worktrees/task"),
        "branch": "task/1",
        "head": "abc",
        "active_pids": [],
        "is_merged": True,
        "pr_state": "Ancestor of main",
    }
    fields.update(overrides)
    return WorktreeInfo(**fields)  # type: ignore[arg-type]


def test_decide_skips_when_processes_cannot_be_verified():
    decision = decide(_worktree(active_pids=None), CleanupOptions(force=True, clean_all=True))
    assert decision.remove is False
    assert "cannot verify" in decision.reason


def test_decide_skips_active_unmerged_and_dirty_worktrees():
    options = CleanupOptions()
    assert decide(_worktree(active_pids=[42]), options).remove is False
    assert decide(_worktree(is_merged=False), options).remove is False
    assert decide(_worktree(is_dirty=True, dirty_count=2), options).remove is False


def test_decide_removes_clean_merged_worktree_and_honours_overrides():
    assert decide(_worktree(), CleanupOptions()).remove is True
    assert decide(_worktree(is_merged=False), CleanupOptions(clean_all=True)).remove is True
    assert decide(_worktree(is_dirty=True), CleanupOptions(force=True)).remove is True


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=_git_env()
    ).stdout


def _git_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.invalid",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.invalid",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
    )
    return env


def _temp_repo_with_merged_worktree(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "README").write_text("temp\n", encoding="utf-8")
    _git(repo, "add", "README")
    _git(repo, "commit", "-q", "-m", "init")
    worktree = repo / ".worktrees" / "merged"
    _git(repo, "worktree", "add", "-q", "-b", "task/merged", str(worktree), "main")
    return repo, worktree.resolve()


def _run_cleanup(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        env=_git_env(),
    )


def test_cleanup_skips_and_reports_worktree_when_proc_is_absent(tmp_path: Path):
    repo, worktree = _temp_repo_with_merged_worktree(tmp_path)

    result = _run_cleanup(repo, "--proc-dir", str(tmp_path / "no-proc"))

    assert result.returncode == 0, result.stderr
    assert "cannot verify" in result.stdout
    assert worktree.exists()
    assert str(worktree) in _git(repo, "worktree", "list")


def test_cleanup_skips_worktree_with_active_process(tmp_path: Path):
    repo, worktree = _temp_repo_with_merged_worktree(tmp_path)
    proc_dir = tmp_path / "proc"
    (proc_dir / "4242").mkdir(parents=True)
    (proc_dir / "4242" / "cwd").symlink_to(worktree)

    result = _run_cleanup(repo, "--proc-dir", str(proc_dir))

    assert "4242" in result.stdout
    assert worktree.exists()


def test_cleanup_removes_merged_idle_worktree_and_branch(tmp_path: Path):
    repo, worktree = _temp_repo_with_merged_worktree(tmp_path)
    proc_dir = tmp_path / "proc"
    proc_dir.mkdir()

    result = _run_cleanup(repo, "--proc-dir", str(proc_dir))

    assert result.returncode == 0, result.stderr
    assert not worktree.exists()
    assert "task/merged" not in _git(repo, "branch", "--list")


def test_cleanup_dry_run_keeps_merged_worktree(tmp_path: Path):
    repo, worktree = _temp_repo_with_merged_worktree(tmp_path)
    proc_dir = tmp_path / "proc"
    proc_dir.mkdir()

    result = _run_cleanup(repo, "--dry-run", "--proc-dir", str(proc_dir))

    assert "WOULD REMOVE" in result.stdout
    assert worktree.exists()
