"""Run the frontend test suite (`pnpm test` in frontend/) from pytest, safely.

The suite starts Node, Vitest and a headless Chromium. Two rules keep it safe under pytest-xdist:
- One run at a time across all workers. Two Vitest browser runs at the same time can collide.
  A file lock serializes them.
- A time limit below the pytest timeout. On timeout the helper stops the whole process group,
  so no Node or Chromium process stays alive after the test.
"""

from __future__ import annotations

import fcntl
import os
import signal
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
SUITE_TIMEOUT_S = 240
_LOCK_PATH = Path(tempfile.gettempdir()) / "runefoble-frontend-suite.lock"


@lru_cache(maxsize=1)
def run_frontend_suite() -> subprocess.CompletedProcess[str]:
    """Run the frontend suite once per process and return the completed result."""
    with _LOCK_PATH.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        proc = subprocess.Popen(
            ["pnpm", "test"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=SUITE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
            stderr += f"\n[frontend suite stopped after {SUITE_TIMEOUT_S}s]"
            return subprocess.CompletedProcess(proc.args, -signal.SIGKILL, stdout, stderr)
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)
