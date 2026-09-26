"""Frontdoor blackbox tests for PR merge conflict detection and resolution."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.backlog_engine.ci_watcher import get_ci_failure_diagnostics
from tools.backlog_engine.git_ops import (
    CIPipelineError,
    commit_and_push,
    sync_branch_with_base,
)
from tools.backlog_engine.github_client import check_pr_conflict_status
from tools.backlog_engine.models import Task, TaskStatus


def _mock_proc(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = ""
    return proc


def test_github_client_detects_clean_pr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that check_pr_conflict_status returns False for clean PRs."""
    data = {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(json.dumps(data)))

    is_bad, reason = check_pr_conflict_status(tmp_path, "https://github.com/example/pr/100")
    assert is_bad is False
    assert reason == ""


def test_github_client_detects_conflicting_pr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that check_pr_conflict_status detects conflicting and dirty PRs."""
    data = {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(json.dumps(data)))

    is_bad, reason = check_pr_conflict_status(tmp_path, "https://github.com/example/pr/101")
    assert is_bad is True
    assert "merge conflicts" in reason


def test_git_ops_sync_branch_with_base_handles_clean_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that sync_branch_with_base succeeds when already up to date."""

    # When rev-list returns 0 behind commits
    def mock_run(cmd, *a, **k):
        if "rev-list" in cmd:
            return _mock_proc("0\n")
        if "rev-parse" in cmd:
            return _mock_proc("hash\n")
        return _mock_proc("")

    # Create dummy .git
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(subprocess, "run", mock_run)

    success, msg = sync_branch_with_base(tmp_path, base_ref="main")
    assert success is True
    assert "already up to date" in msg


def test_commit_and_push_raises_on_merge_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that commit_and_push raises CIPipelineError when merge-tree detects conflicts."""
    task = Task(
        id="0091", title="Test", status=TaskStatus.IN_PROGRESS, file_path=tmp_path / "0091.md"
    )

    def mock_run(cmd, *a, **k):
        if "rev-list" in cmd:
            return _mock_proc("3\n")
        if "merge-tree" in cmd:
            return _mock_proc("CONFLICT in orchestrator.py", returncode=1)
        return _mock_proc("")

    monkeypatch.setattr(subprocess, "run", mock_run)
    with pytest.raises(CIPipelineError) as exc_info:
        commit_and_push(tmp_path, task, "feat/0091-test")
    assert "has merge conflicts" in str(exc_info.value)


def test_diagnostics_categorizes_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that get_ci_failure_diagnostics categorizes conflicting PR as 'conflict'."""
    data = {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(json.dumps(data)))

    category, details = get_ci_failure_diagnostics(tmp_path, "https://github.com/example/pr/102")
    assert category == "conflict"
    assert "merge conflicts" in details
