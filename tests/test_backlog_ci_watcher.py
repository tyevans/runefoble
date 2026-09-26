"""Frontdoor tests for GitHub PR conflict detection and CI watcher status polling."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.backlog_engine import ci_watcher


def _mock_proc(stdout: str, returncode: int = 0) -> MagicMock:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = ""
    return proc


def test_check_pr_conflict_status_clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that a clean mergeable PR returns (False, '')."""
    data = {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(json.dumps(data)))

    is_bad, reason = ci_watcher.check_pr_conflict_status(
        tmp_path, "https://github.com/example/pr/1"
    )
    assert is_bad is False
    assert reason == ""


def test_check_pr_conflict_status_conflicting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that a conflicting PR (CONFLICTING/DIRTY) is detected immediately."""
    data = {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(json.dumps(data)))

    is_bad, reason = ci_watcher.check_pr_conflict_status(
        tmp_path, "https://github.com/example/pr/7"
    )
    assert is_bad is True
    assert "merge conflicts" in reason
    assert "CONFLICTING" in reason
    assert "DIRTY" in reason


def test_check_pr_conflict_status_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that a closed PR is detected and rejected."""
    data = {"state": "CLOSED", "mergeable": "UNKNOWN", "mergeStateStatus": "UNKNOWN"}
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(json.dumps(data)))

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
        if "view" in cmd:
            data = {"state": "OPEN", "mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
            return _mock_proc(json.dumps(data))
        if "checks" in cmd:
            check_poll_count += 1
            proc = _mock_proc("", returncode=1)
            proc.stderr = "no checks reported on the 'feat/test' branch"
            return proc
        return _mock_proc("")

    monkeypatch.setattr(subprocess, "run", mock_run)

    passed = ci_watcher.wait_for_ci_checks(
        tmp_path, "https://github.com/example/pr/7", poll_interval=0, timeout_seconds=10
    )
    assert passed is False
    assert check_poll_count == 0


def test_close_pull_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that close_pull_request invokes gh pr close with comment."""
    captured_cmd = None

    def mock_run(cmd, *args, **kwargs):
        nonlocal captured_cmd
        captured_cmd = cmd
        return _mock_proc("Closed PR")

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


def test_fetch_failed_ci_logs_extracts_run_logs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that fetch_failed_ci_logs extracts action run id and invokes gh run view --log-failed."""
    captured_cmd = None

    def mock_run(cmd, *a, **k):
        nonlocal captured_cmd
        captured_cmd = cmd
        return _mock_proc("FAILED tests/test_foo.py::test_bar - AssertionError")

    monkeypatch.setattr(subprocess, "run", mock_run)
    failed = [
        {
            "name": "Python Lint, Tests & Properties",
            "state": "FAILURE",
            "link": "https://github.com/tyevans/runefoble/actions/runs/36256607306/job/108444460615",
        }
    ]
    log = ci_watcher.fetch_failed_ci_logs(tmp_path, failed)
    assert "AssertionError" in log
    assert captured_cmd == [
        "gh",
        "run",
        "view",
        "36256607306",
        "--log-failed",
        "--job",
        "108444460615",
    ]
