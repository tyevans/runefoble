"""Blackbox test for the single file-length gate (Hard Invariant 6, TASK-0681).

The gate is the `make health-check` script. The test runs the script as a
process in a temporary repository layout. It checks the exit status and the
printed output. It does not read the script's internals.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HEALTH_CHECK = REPO_ROOT / "scripts" / "health_check.py"


def _make_repo(tmp_path: Path) -> Path:
    """Copy the health-check script into a temporary repository root."""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(HEALTH_CHECK, root / "scripts" / "health_check.py")
    return root


def _run_gate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "health_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )


def test_health_check_fails_when_source_file_exceeds_500_lines(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    libs = root / "libs" / "demo_pkg"
    libs.mkdir(parents=True)
    (libs / "oversized_module.py").write_text("x = 1\n" * 501, encoding="utf-8")

    result = _run_gate(root)

    assert result.returncode != 0
    assert "oversized_module.py" in result.stdout
    assert "INVARIANT VIOLATIONS" in result.stdout


def test_health_check_passes_when_all_source_files_fit_the_limit(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    libs = root / "libs" / "demo_pkg"
    libs.mkdir(parents=True)
    (libs / "small_module.py").write_text("x = 1\n" * 500, encoding="utf-8")

    result = _run_gate(root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Zero source files exceed 500 lines" in result.stdout
