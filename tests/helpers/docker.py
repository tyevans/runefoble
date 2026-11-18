"""Docker CLI access for test fixtures. Every call has a time limit."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from tests.helpers.process import run_command

# Upper bound for one Docker CLI call. The image pull is the slowest call.
DOCKER_TIMEOUT_SECONDS = 180.0


def docker_bin() -> str | None:
    """Return the path of the docker CLI, or None when it is not on PATH."""
    return shutil.which("docker")


def require_docker_bin() -> str:
    """Return the docker CLI path. Raise when the CLI is missing."""
    path = docker_bin()
    if not path:
        raise RuntimeError("Docker is required but the docker CLI is not on PATH")
    return path


def run_docker(
    docker: str, args: Sequence[str], *, timeout: float
) -> subprocess.CompletedProcess[str]:
    """Run `docker <args>` and capture its text output. Return the result without checking it."""
    return run_command([docker, *args], check=False, timeout=timeout)
