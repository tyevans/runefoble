"""Blackbox tests for the `make lint` and `make test-mutation` quality targets (TASK-0726)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

FAKE_UV = """#!/bin/sh
# Stands in for `uv` so that the test does not run a real mutation campaign.
if [ "$3" = "run" ]; then exit "${FAKE_MUTMUT_RUN_EXIT:-0}"; fi
if [ "$3" = "results" ]; then printf '%s\\n' "$FAKE_MUTMUT_RESULTS"; exit 0; fi
exit 97
"""


def _run_test_mutation(
    tmp_path: Path, results: str, run_exit: int = 0
) -> subprocess.CompletedProcess[str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(FAKE_UV, encoding="utf-8")
    fake_uv.chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "FAKE_MUTMUT_RESULTS": results,
        "FAKE_MUTMUT_RUN_EXIT": str(run_exit),
    }
    return subprocess.run(
        ["make", "--no-print-directory", "test-mutation"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_make_lint_runs_helm_lint() -> None:
    result = subprocess.run(
        ["make", "-n", "lint"], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("helm lint ") == 1


def test_make_test_mutation_fails_and_reports_survivors(tmp_path: Path) -> None:
    result = _run_test_mutation(
        tmp_path, "    runefoble_platform.x__mutmut_1: survived\n    y__mutmut_2: no tests"
    )

    assert result.returncode != 0
    assert "runefoble_platform.x__mutmut_1: survived" in result.stdout
    assert "1 mutant(s) survived" in result.stdout


def test_make_test_mutation_passes_without_survivors(tmp_path: Path) -> None:
    result = _run_test_mutation(tmp_path, "")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "No surviving mutants" in result.stdout


def test_make_test_mutation_fails_when_mutmut_run_fails(tmp_path: Path) -> None:
    result = _run_test_mutation(tmp_path, "", run_exit=3)

    assert result.returncode != 0
    assert "No surviving mutants" not in result.stdout
