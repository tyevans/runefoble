"""Run Node test suites from pytest, safely.

Node suites start child processes such as Vitest and headless Chromium. Two rules keep them safe
under pytest-xdist:
- One run at a time per lock file. A file lock serializes the workers.
- A time limit below the pytest timeout. On timeout the helper stops the whole process group,
  so no child process stays alive after the test.
"""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
NODE_SUITE_LOCK_PATH = Path(tempfile.gettempdir()) / "runefoble-node-suite.lock"


NODE_TEST_TIMEOUT_S = 120.0


def run_node_tests(
    test_files: Sequence[Path], *, timeout: float
) -> subprocess.CompletedProcess[str]:
    """Run TypeScript test files with the Node test runner, one run at a time.

    On timeout the result has a negative return code and a note in stderr. The caller asserts on
    the return code, so a timeout fails the test.
    """
    return run_locked_group(
        ["node", "--experimental-strip-types", "--test", *(str(path) for path in test_files)],
        cwd=REPO_ROOT,
        timeout=timeout,
        lock_path=NODE_SUITE_LOCK_PATH,
    )


def run_locked_group(
    args: list[str],
    *,
    cwd: Path,
    timeout: float,
    lock_path: Path,
) -> subprocess.CompletedProcess[str]:
    """Run a command in its own process group, one run at a time per lock file.

    On timeout the whole group receives SIGKILL. The result then has a negative return code and
    a note in stderr that names the time limit.
    """
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        proc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            stderr += f"\n[{args[0]} run stopped after {timeout}s]"
            return subprocess.CompletedProcess(proc.args, -signal.SIGKILL, stdout, stderr)
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
