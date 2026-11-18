"""Blackbox tests for the health gate (Hard Invariant 6, TASK-0668).

The gate is `make health-check`, which runs `spec-ops health` and
`spec-ops schema check`. The tests run the gate as a process in a temporary
repository. They check exit status and printed output only.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_repo(tmp_path: Path) -> Path:
    """Create a temporary repository that carries the spec-ops configuration."""
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copy(REPO_ROOT / "specops.toml", root / "specops.toml")
    return root


def _run_health(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["spec-ops", "health"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_lines(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * count, encoding="utf-8")


@pytest.mark.parametrize("directory", ["libs", "scripts", "e2e", "tools"])
def test_health_gate_fails_when_source_file_exceeds_500_lines(
    tmp_path: Path, directory: str
) -> None:
    root = _make_repo(tmp_path)
    _write_lines(root / directory / "oversized_module.py", 501)

    result = _run_health(root)

    assert result.returncode != 0
    assert "oversized_module.py" in result.stdout
    assert "File Length Violation" in result.stdout


def test_health_gate_reports_no_violation_when_files_fit_the_limit(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_lines(root / "e2e" / "steps" / "small_steps.ts", 500)

    result = _run_health(root)

    assert "File Length Violation" not in result.stdout
    assert "Zero source files exceed" in result.stdout


def test_make_health_check_invokes_spec_ops_gates() -> None:
    result = subprocess.run(
        ["make", "-n", "health-check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "spec-ops health" in result.stdout
    assert "spec-ops schema check" in result.stdout
    assert "health_check.py" not in result.stdout
