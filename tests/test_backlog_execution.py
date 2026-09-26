"""Tests for backlog execution pipeline, repair loops, rollback hooks, and gates."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.backlog_engine import ci_watcher, orchestrator
from tools.backlog_engine.agent_worker import build_repair_prompt
from tools.backlog_engine.models import Task, TaskStatus
from tools.backlog_engine.queue import BacklogQueue
from tools.backlog_engine.worktree import run_preflight_checks


def _mock_proc(code: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], code, out, err)


@pytest.fixture
def mock_orch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Mocks worktree lifecycle and branch merging for orchestrator pipeline tests."""
    cleanup = MagicMock()
    monkeypatch.setattr(orchestrator, "create_worktree", MagicMock(return_value=tmp_path / "wt"))
    monkeypatch.setattr(orchestrator, "cleanup_worktree", cleanup)
    monkeypatch.setattr(orchestrator, "merge_local_branch", MagicMock())
    return cleanup


def test_task_claiming_lifecycle(tmp_path: Path):
    """Verifies atomic state transitions: claim -> review -> complete."""
    b = tmp_path / "backlog"
    (b / "complete").mkdir(parents=True)
    (b / "refined").mkdir(parents=True)
    (b / "PRIORITY.md").write_text("1. **TASK-0002 (Refined)**: [0002.md](refined/0002.md)\n")
    t2 = b / "refined" / "0002.md"
    t2.write_text("---\nid: 0002\ntitle: T2\nstatus: Refined\n---\nBody")

    queue = BacklogQueue(b)
    task = queue.get_ready_unblocked_tasks()[0]
    queue.claim_task(task, worker_id="worker-test", branch="feat/0002")
    assert task.status == TaskStatus.IN_PROGRESS and len(queue.get_ready_unblocked_tasks()) == 0

    queue.mark_review(task, pr_url="https://github.com/example/pr/1")
    assert task.status == TaskStatus.REVIEW and task.pr_url == "https://github.com/example/pr/1"

    new_p = queue.complete_task(task)
    assert task.status == TaskStatus.COMPLETE and new_p.parent.name == "complete"
    assert not t2.exists() and new_p.exists()
    assert "**TASK-0002 (Complete)**" in (b / "PRIORITY.md").read_text()


def test_build_repair_prompt():
    """Verifies that the repair prompt includes the error log and clear invariant guidance."""
    task = Task(id="0024", title="SpiceDB", status=TaskStatus.READY, file_path=Path("/d/p.md"))
    log = "❌ Pre-flight check 'Ruff Format' failed: unformatted: docs/how-to.md"
    prompt = build_repair_prompt(task, log)
    assert "TASK-0024" in prompt and "SpiceDB" in prompt and "PRE-FLIGHT VERIFICATION LOG" in prompt
    assert "uv run ruff format ." in prompt and "uv run pytest" in prompt


def test_preflight_checks_aggregates_multiple_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verifies that run_preflight_checks collects multiple failures instead of exiting on first."""

    def mock_run(cmd, *a, **k):
        out = (
            "Lint err"
            if "check" in cmd
            else ("Format err" if "format" in cmd else "Pytest Suite passed")
        )
        return _mock_proc(1 if ("check" in cmd or "format" in cmd) else 0, out=out)

    monkeypatch.setattr(subprocess, "run", mock_run)
    passed, log = run_preflight_checks(tmp_path)
    assert passed is False and "Pre-flight check 'Ruff Lint' failed" in log
    assert "Pre-flight check 'Ruff Format' failed" in log and "Pytest Suite passed" in log


def test_orchestrator_repair_loop_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_orch
):
    """Verifies that the orchestrator retries preflight with agent feedback and succeeds."""
    task = Task(id="0099", title="Repair", status=TaskStatus.READY, file_path=tmp_path / "0099.md")
    mock_queue, preflight_calls, calls = MagicMock(), 0, []

    def mock_preflight(wt):
        nonlocal preflight_calls
        preflight_calls += 1
        return (preflight_calls > 1), ("Fail" if preflight_calls == 1 else "OK")

    monkeypatch.setattr(orchestrator, "run_preflight_checks", mock_preflight)
    monkeypatch.setattr(
        orchestrator,
        "run_agent_in_worktree",
        lambda wt, t, feedback=None: calls.append(feedback) or (True, "Fixed"),
    )

    res = orchestrator.execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True)
    assert res.success is True and calls == [None, "Fail"] and preflight_calls == 2
    mock_queue.complete_task.assert_called_once_with(task)


def test_orchestrator_repair_loop_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_orch
):
    """Verifies that repeated preflight failures exit cleanly after max repair attempts."""
    task = Task(id="0099", title="Broken", status=TaskStatus.READY, file_path=tmp_path / "0099.md")
    mock_queue = MagicMock()
    monkeypatch.setattr(
        orchestrator, "run_preflight_checks", lambda wt: (False, "Persistent Failure")
    )
    monkeypatch.setattr(
        orchestrator, "run_agent_in_worktree", lambda wt, t, feedback=None: (True, "Done")
    )

    res = orchestrator.execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True)
    assert not res.success and "Persistent Failure" in res.message
    assert "Pre-flight checks failed after 3 repair attempt(s)" in res.message
    mock_queue.complete_task.assert_not_called()
    mock_queue.release_task.assert_called_once_with(task)
    mock_orch.assert_called_once()


def test_orchestrator_releases_task_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mock_orch
):
    """Verifies that execute_task_pipeline catches KeyboardInterrupt and releases the task."""
    task = Task(id="0099", title="Int", status=TaskStatus.READY, file_path=tmp_path / "0099.md")
    mock_queue = MagicMock()
    monkeypatch.setattr(
        orchestrator, "run_agent_in_worktree", MagicMock(side_effect=KeyboardInterrupt())
    )

    with pytest.raises(KeyboardInterrupt):
        orchestrator.execute_task_pipeline(task, tmp_path, mock_queue, local_mode=True)

    mock_queue.claim_task.assert_called_once()
    mock_queue.release_task.assert_called_once_with(task)
    mock_orch.assert_called_once()


def test_wait_for_ci_checks_success_after_pending(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that wait_for_ci_checks waits through unregistered and pending checks to success."""
    p_json = json.dumps([{"name": "Lint", "state": "IN_PROGRESS", "bucket": "pending"}])
    s_json = json.dumps([{"name": "Lint", "state": "SUCCESS", "bucket": "pass"}])
    v_json = json.dumps({"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "BLOCKED"})
    polls = [
        _mock_proc(1, err="no checks reported"),
        _mock_proc(8, out=p_json),
        _mock_proc(0, out=s_json),
    ]

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, *a, **k: _mock_proc(out=v_json) if "view" in cmd else polls.pop(0),
    )
    passed = ci_watcher.wait_for_ci_checks(
        tmp_path, "https://github.com/example/pr/1", poll_interval=0, timeout_seconds=10
    )
    assert passed is True and len(polls) == 0


def test_wait_for_ci_checks_failure_and_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies that wait_for_ci_checks detects failed check runs and timeout conditions."""
    fail_p = _mock_proc(1, out=json.dumps([{"name": "Lint", "state": "FAILURE"}]))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fail_p)
    assert not ci_watcher.wait_for_ci_checks(
        tmp_path, "https://pr/1", poll_interval=0, timeout_seconds=10
    )

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _mock_proc(1, err="no checks"))
    assert not ci_watcher.wait_for_ci_checks(
        tmp_path, "https://pr/1", poll_interval=0.01, timeout_seconds=0.03
    )
