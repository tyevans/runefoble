"""Blackbox frontdoor tests: the PostgreSQL test fixture fails loudly and cleans up its temp file.

Governed by:
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Frontdoors used: the `postgres_service` fixture, run in child pytest processes, and the pytest
exit status and output. The Docker CLI is replaced by a fake `docker` script on PATH. That script
is a process boundary, so the fixture code under test is the real code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[1]
HOLD_MODULE = "tests/helpers/postgres_hold_child.py"
CHILD_TIMEOUT_SECONDS = 300.0

FAKE_DOCKER_SCRIPT = """#!/bin/sh
case "$1" in
  info)
    {info_behaviour}
    ;;
  run)
    echo "pull access denied: simulated run failure" >&2
    exit 1
    ;;
  *)
    exit 0
    ;;
esac
"""


def _write_fake_docker(bin_dir: Path, info_behaviour: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER_SCRIPT.format(info_behaviour=info_behaviour), encoding="utf-8")
    docker.chmod(0o755)


def _run_fixture_child(
    tmp_path: Path, path_dirs: list[Path], tmpdir: Path
) -> subprocess.CompletedProcess[str]:
    """Run the postgres fixture in a child pytest process with a controlled PATH and TMPDIR."""
    tmpdir.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.pathsep.join(str(path) for path in path_dirs),
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "TMPDIR": str(tmpdir),
        "RUNEFOBLE_HOLD_INFO_FILE": str(tmp_path / "info.json"),
        "RUNEFOBLE_HOLD_MODE": "exit",
    }
    return run_command(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", HOLD_MODULE],
        cwd=REPO_ROOT,
        env=env,
        timeout=CHILD_TIMEOUT_SECONDS,
        check=False,
    )


def _leftover_temp_scripts(tmpdir: Path) -> list[str]:
    return sorted(path.name for path in tmpdir.glob("*.sh"))


def test_docker_cli_missing_skips_with_reason(tmp_path):
    empty_path_dir = tmp_path / "no-docker"
    empty_path_dir.mkdir()
    result = _run_fixture_child(tmp_path, [empty_path_dir], tmp_path / "tmp")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skipped" in result.stdout
    assert "Docker is not available" in result.stdout


def test_docker_daemon_unreachable_skips_with_reason(tmp_path):
    bin_dir = tmp_path / "bin"
    _write_fake_docker(bin_dir, "echo 'Cannot connect to the Docker daemon' >&2; exit 1")
    result = _run_fixture_child(tmp_path, [bin_dir], tmp_path / "tmp")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "skipped" in result.stdout
    assert "Cannot connect to the Docker daemon" in result.stdout


def test_container_start_failure_fails_the_test_with_the_error(tmp_path):
    bin_dir = tmp_path / "bin"
    _write_fake_docker(bin_dir, "exit 0")
    result = _run_fixture_child(tmp_path, [bin_dir], tmp_path / "tmp")

    assert result.returncode != 0, result.stdout + result.stderr
    assert "simulated run failure" in result.stdout + result.stderr
    assert "skipped" not in result.stdout


@pytest.mark.skipif(shutil.which("docker") is None, reason="Docker is not available")
def test_fixture_removes_its_temp_script_after_teardown(tmp_path):
    tmpdir = tmp_path / "tmp"
    result = _run_fixture_child(
        tmp_path, [Path(shutil.which("docker")).parent, Path(sys.executable).parent], tmpdir
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert _leftover_temp_scripts(tmpdir) == []


def test_temp_script_is_removed_when_the_container_fails_to_start(tmp_path):
    bin_dir = tmp_path / "bin"
    _write_fake_docker(bin_dir, "exit 0")
    tmpdir = tmp_path / "tmp"
    result = _run_fixture_child(tmp_path, [bin_dir], tmpdir)

    assert result.returncode != 0
    assert _leftover_temp_scripts(tmpdir) == []
