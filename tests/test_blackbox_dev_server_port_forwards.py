"""Blackbox test: dev server children stop with their parent (TASK-0801).

The dev server runs against a fake `kubectl` and a fake `uv` placed first on PATH. Both fakes
record their PID and then sleep. No real cluster is reached. The Redis endpoint is a loopback
socket that the test holds open, so the dev server does not need a Redis port-forward.

Governed by ADR-0005. Part of TASK-0801.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.polling import wait_until
from tests.helpers.ports import free_port

REPO_ROOT = Path(__file__).resolve().parent.parent

# Each fake records its own PID in a marker file name, then sleeps. `exec` keeps the PID.
FAKE_KUBECTL = """#!/bin/sh
case "$1" in
  get) exit 0 ;;
  port-forward) touch "$FAKE_PROCESS_DIR/kubectl-port-forward.$$"; exec sleep 300 ;;
esac
exit 1
"""

FAKE_UV = """#!/bin/sh
touch "$FAKE_PROCESS_DIR/uv.$$"
exec sleep 300
"""

CHILD_MARKERS = ("kubectl-port-forward", "uv")


def wait_for(predicate, timeout: float) -> bool:
    """Poll a condition until it holds or the timeout expires."""
    return wait_until(predicate, timeout_s=timeout, interval_s=0.1)


def recorded_pids(markers: Path) -> list[int]:
    """Return the PIDs of every fake child that the dev server started."""
    pids: list[int] = []
    for prefix in CHILD_MARKERS:
        for marker in markers.glob(f"{prefix}.*"):
            pids.append(int(marker.name.rsplit(".", 1)[1]))
    return sorted(pids)


def is_alive(pid: int) -> bool:
    """True when the PID names a running process. A zombie has already exited."""
    try:
        with open(f"/proc/{pid}/stat", encoding="utf-8") as stat:
            state = stat.read().rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return False
    return state != "Z"


def write_fake(bin_dir: Path, name: str, body: str) -> None:
    """Write an executable fake command into the directory placed first on PATH."""
    script = bin_dir / name
    script.write_text(body, encoding="utf-8")
    script.chmod(0o755)


def stop_survivors(markers: Path) -> None:
    """Kill every recorded fake child that is still running. The test started all of them."""
    for pid in recorded_pids(markers):
        if is_alive(pid):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="PR_SET_PDEATHSIG is Linux-only")
@pytest.mark.parametrize("stop_signal", [signal.SIGKILL, signal.SIGTERM])
def test_dev_server_children_stop_when_dev_server_stops(
    tmp_path: Path, stop_signal: signal.Signals
) -> None:
    """Stopping the dev server stops its port-forward and gateway children within 5 seconds.

    SIGKILL gives the dev server no chance to clean up. The kernel must stop the children.
    """
    bin_dir = tmp_path / "bin"
    markers = tmp_path / "markers"
    bin_dir.mkdir()
    markers.mkdir()
    write_fake(bin_dir, "kubectl", FAKE_KUBECTL)
    write_fake(bin_dir, "uv", FAKE_UV)

    # A held listener makes the Redis check pass without a port-forward.
    redis_listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    redis_listener.bind(("127.0.0.1", 0))
    redis_listener.listen()
    redis_port = redis_listener.getsockname()[1]

    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("SPICEDB_ENDPOINT", "RUNEFOBLE_SPICEDB_ENDPOINT", "REDIS_URL")
    }
    env["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
    env["FAKE_PROCESS_DIR"] = str(markers)
    env["RUNEFOBLE_REDIS_URL"] = f"redis://127.0.0.1:{redis_port}/0"

    log_path = tmp_path / "dev_server.log"
    with log_path.open("w", encoding="utf-8") as log:
        # A closed SpiceDB port forces a `kubectl port-forward` child.
        proc = subprocess.Popen(
            [
                sys.executable,
                "scripts/dev_server.py",
                "--gateway-port",
                str(free_port()),
                "--spicedb-port",
                str(free_port()),
                "--no-frontend",
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            started = wait_for(
                lambda: (
                    proc.poll() is not None
                    or (any(markers.glob("kubectl-port-forward.*")) and any(markers.glob("uv.*")))
                ),
                timeout=30.0,
            )
            output = log_path.read_text(encoding="utf-8")
            assert proc.poll() is None, f"dev server exited early:\n{output}"
            assert started, f"fake children never started:\n{output}"
            children = recorded_pids(markers)
            assert children, "no fake child recorded its PID"

            os.kill(proc.pid, stop_signal)
            proc.wait(timeout=15.0)

            survived = wait_for(lambda: not any(is_alive(pid) for pid in children), timeout=5.0)
            alive_now = [pid for pid in children if is_alive(pid)]
            assert survived, f"children still alive after dev server stopped: {alive_now}"
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10.0)
            stop_survivors(markers)
            redis_listener.close()
