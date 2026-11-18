"""Blackbox frontdoor test: a killed pytest run leaves no test container behind.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: Core Event Sourcing with eventsource-py
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Frontdoors used: the `postgres_service` fixture, run in child pytest processes, and `docker ps`
as the observable result. The test starts and kills only its own child processes and the
containers that those children start.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLD_MODULE = "tests/helpers/postgres_hold_child.py"
REDIS_HOLD_MODULE = "tests/helpers/redis_hold_child.py"
START_TIMEOUT_SECONDS = 180.0

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not available")


def _start_child(
    tmp_path: Path, name: str, mode: str, module: str = HOLD_MODULE
) -> tuple[subprocess.Popen[bytes], Path]:
    """Run a hold module in a child pytest process. Return the process and its info file."""
    info_path = tmp_path / f"{name}.json"
    log = (tmp_path / f"{name}.log").open("wb")
    env = {
        **os.environ,
        "RUNEFOBLE_HOLD_INFO_FILE": str(info_path),
        "RUNEFOBLE_HOLD_MODE": mode,
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", module],
        cwd=REPO_ROOT,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    return process, info_path


def _wait_for_container_name(process: subprocess.Popen[bytes], info_path: Path) -> str:
    """Wait until the child writes its container name. Fail if the child exits first."""
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if info_path.exists():
            return str(json.loads(info_path.read_text(encoding="utf-8"))["container_name"])
        if process.poll() is not None:
            pytest.fail(f"child pytest exited with {process.returncode} before it started")
        time.sleep(0.5)
    pytest.fail("child pytest did not start a container in time")


def _running_containers(name: str) -> list[str]:
    """Return the ids of running containers with this exact name."""
    result = subprocess.run(
        ["docker", "ps", "-q", "--filter", f"name=^{name}$"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split()


def _remove_own_container(name: str) -> None:
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def test_orphaned_container_is_removed_on_next_run_and_live_owner_keeps_its_container(tmp_path):
    orphan_child, orphan_info = _start_child(tmp_path, "orphan", "hold")
    live_child, live_info = _start_child(tmp_path, "live", "hold")
    orphan_name = live_name = ""
    try:
        orphan_name = _wait_for_container_name(orphan_child, orphan_info)
        live_name = _wait_for_container_name(live_child, live_info)

        # The owner of the orphan dies without teardown. Reap it, then confirm it is gone.
        orphan_child.kill()
        orphan_child.wait(timeout=30)
        assert _running_containers(orphan_name), "precondition: the orphan must be running"

        # Next run: the session start reaps the orphan before any container starts.
        next_child, next_info = _start_child(tmp_path, "next", "exit")
        assert next_child.wait(timeout=START_TIMEOUT_SECONDS) == 0, (
            tmp_path / "next.log"
        ).read_text(encoding="utf-8", errors="replace")
        assert next_info.exists()

        assert _running_containers(orphan_name) == [], "the orphaned container must be removed"
        assert _running_containers(live_name), "a container of a live owner must keep running"
    finally:
        for child in (orphan_child, live_child):
            if child.poll() is None:
                child.send_signal(signal.SIGKILL)
                child.wait(timeout=30)
        for name in (orphan_name, live_name):
            if name:
                _remove_own_container(name)


def test_orphaned_redis_container_is_removed_at_next_session_start(tmp_path):
    orphan_child, orphan_info = _start_child(tmp_path, "redis-orphan", "hold", REDIS_HOLD_MODULE)
    orphan_name = ""
    try:
        orphan_name = _wait_for_container_name(orphan_child, orphan_info)

        orphan_child.kill()
        orphan_child.wait(timeout=30)
        assert _running_containers(orphan_name), "precondition: the orphaned Redis must be running"

        next_child, next_info = _start_child(tmp_path, "next-redis", "exit", HOLD_MODULE)
        assert next_child.wait(timeout=START_TIMEOUT_SECONDS) == 0, (
            tmp_path / "next-redis.log"
        ).read_text(encoding="utf-8", errors="replace")
        assert next_info.exists()

        assert _running_containers(orphan_name) == [], "the orphaned Redis must be removed"
    finally:
        if orphan_child.poll() is None:
            orphan_child.send_signal(signal.SIGKILL)
            orphan_child.wait(timeout=30)
        if orphan_name:
            _remove_own_container(orphan_name)
