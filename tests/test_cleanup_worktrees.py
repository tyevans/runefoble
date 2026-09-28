"""Tests for scripts/cleanup_worktrees.py git worktree maintenance tool."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from scripts.cleanup_worktrees import (
    WorktreeInfo,
    cleanup_worktrees,
    find_active_pids_for_path,
    is_branch_merged,
    parse_worktrees,
)


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


def test_find_active_pids_for_path(tmp_path: Path):
    target = tmp_path / "worktree"
    target.mkdir()

    with (
        patch("os.readlink") as mock_readlink,
        patch("scripts.cleanup_worktrees.Path.iterdir") as mock_iter,
    ):
        mock_iter.return_value = [
            Path("/proc/12345"),
            Path("/proc/99999"),
            Path("/proc/self"),
        ]
        mock_readlink.side_effect = lambda p: (
            str(target / "subdir") if "12345" in str(p) else "/other/path"
        )

        pids = find_active_pids_for_path(target)
        assert pids == [12345]


def test_cleanup_worktrees_dry_run_skips_active_and_dirty():
    repo_root = Path("/mock/repo")
    mock_wts = [
        WorktreeInfo(path=repo_root, branch="main", head="abc", is_main=True),
        WorktreeInfo(
            path=Path("/mock/repo/.worktrees/active"),
            branch="feat/active",
            head="111",
            active_pids=[42],
            is_merged=True,
        ),
        WorktreeInfo(
            path=Path("/mock/repo/.worktrees/dirty"),
            branch="feat/dirty",
            head="222",
            active_pids=[],
            is_dirty=True,
            dirty_count=2,
            is_merged=True,
        ),
        WorktreeInfo(
            path=Path("/mock/repo/.worktrees/clean-merged"),
            branch="feat/clean-merged",
            head="333",
            active_pids=[],
            is_dirty=False,
            is_merged=True,
            pr_state="Merged PR",
        ),
    ]

    with (
        patch("scripts.cleanup_worktrees.inspect_worktrees", return_value=mock_wts),
        patch("scripts.cleanup_worktrees.run_cmd") as mock_run,
    ):
        ret = cleanup_worktrees(repo_root, dry_run=True, force=False)
        assert ret == 0
        # Under dry-run, git worktree remove is never called
        for call_args in mock_run.call_args_list:
            assert "remove" not in call_args[0][0]


def test_cleanup_worktrees_removes_clean_merged_worktree():
    repo_root = Path("/mock/repo")
    target_path = Path("/mock/repo/.worktrees/clean-merged")
    mock_wts = [
        WorktreeInfo(path=repo_root, branch="main", head="abc", is_main=True),
        WorktreeInfo(
            path=target_path,
            branch="feat/clean-merged",
            head="333",
            active_pids=[],
            is_dirty=False,
            is_merged=True,
            pr_state="Ancestor of origin/main",
        ),
    ]

    with (
        patch("scripts.cleanup_worktrees.inspect_worktrees", return_value=mock_wts),
        patch("scripts.cleanup_worktrees.run_cmd") as mock_run,
    ):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="")
        ret = cleanup_worktrees(repo_root, dry_run=False, force=False)
        assert ret == 0

        # Verify git worktree remove was called
        executed_cmds = [call_args[0][0] for call_args in mock_run.call_args_list]
        assert ["git", "worktree", "remove", str(target_path)] in executed_cmds
        assert ["git", "branch", "-d", "feat/clean-merged"] in executed_cmds
        assert ["git", "worktree", "prune"] in executed_cmds
