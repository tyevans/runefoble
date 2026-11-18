"""Run the frontend test suite (`pnpm test` in frontend/) from pytest, safely.

The suite starts Node, Vitest and a headless Chromium. Two rules keep it safe under pytest-xdist:
- One run at a time across all workers. Two Vitest browser runs at the same time can collide.
  A file lock serializes them.
- A time limit below the pytest timeout. On timeout the helper stops the whole process group,
  so no Node or Chromium process stays alive after the test.
"""

from __future__ import annotations

import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from tests.helpers.node_suite import run_locked_group

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = REPO_ROOT / "frontend"
SUITE_TIMEOUT_S = 240
_LOCK_PATH = Path(tempfile.gettempdir()) / "runefoble-frontend-suite.lock"


@lru_cache(maxsize=1)
def run_frontend_suite() -> subprocess.CompletedProcess[str]:
    """Run the frontend suite once per process and return the completed result."""
    return run_locked_group(
        ["pnpm", "test"],
        cwd=FRONTEND_DIR,
        timeout=SUITE_TIMEOUT_S,
        lock_path=_LOCK_PATH,
    )
