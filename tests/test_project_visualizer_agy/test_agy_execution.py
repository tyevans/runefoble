"""Tests for AGY background process execution, output streaming, and termination lifecycle."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from tools.project_visualizer.agy_runner import AgyRunnerManager


def test_agy_runner_execution_and_lifecycle(repo_root: Path, mock_agy_bin: Path):
    runner = AgyRunnerManager(repo_root, agy_bin=str(mock_agy_bin))

    job = runner.launch_job(
        prompt="Build feature for TASK-0042",
        continue_session=True,
        target_entity_id="TASK-0042",
    )

    assert job.status in ("pending", "running")
    assert job.job_id.startswith("agy-")
    assert job.target_entity_id == "TASK-0042"
    assert job.continue_session is True

    for _ in range(50):
        if job.status in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert job.status == "completed"
    assert job.exit_code == 0
    assert "Mock AGY executed: prompt='Build feature for TASK-0042', continue=True" in job.output
    assert job.end_time is not None

    fetched = runner.get_job(job.job_id)
    assert fetched is job

    recent = runner.list_jobs()
    assert len(recent) == 1
    assert recent[0].job_id == job.job_id


def test_agy_runner_termination(repo_root: Path, mock_agy_bin: Path):
    runner = AgyRunnerManager(repo_root, agy_bin=str(mock_agy_bin))

    job = runner.launch_job(prompt="--sleep testing timeout")
    time.sleep(0.1)

    assert job.status in ("pending", "running")
    terminated = runner.terminate_job(job.job_id)
    assert terminated is True

    time.sleep(0.1)
    assert job.status == "terminated"
    assert "[Process terminated by user]" in job.output

    assert runner.terminate_job(job.job_id) is False
    assert runner.terminate_job("nonexistent-job") is False


def test_agy_runner_failed_exit_code(repo_root: Path):
    runner = AgyRunnerManager(repo_root, agy_bin=sys.executable)
    # python with flags --dangerously-skip-permissions -p ... fails with unrecognized arguments
    job = runner.launch_job(prompt="Failing command")

    for _ in range(50):
        if job.status in ("completed", "failed"):
            break
        time.sleep(0.05)

    assert job.status == "failed"
    assert job.exit_code != 0
