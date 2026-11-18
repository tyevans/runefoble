"""Blackbox test for backlog link, status, path, and governance drift (TASK-0666).

The check is `scripts/check_backlog_links.py`. It reads repository files only. The test
runs the check as a process and asserts that every category reports zero. It reads the
JSON output and does not inspect source text.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK = REPO_ROOT / "scripts" / "check_backlog_links.py"


def test_backlog_records_have_no_drift() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECK), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    report = json.loads(result.stdout)
    non_zero = {name: entry["count"] for name, entry in report.items() if entry["count"]}
    assert non_zero == {}
