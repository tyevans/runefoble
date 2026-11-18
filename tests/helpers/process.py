"""Run external commands from tests. Every call has a time limit.

`subprocess.run` without a timeout can block a test run forever when a child process hangs.
`run_command` makes the limit a required keyword, so no caller can omit it.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path


def run_command(
    args: Sequence[str],
    *,
    timeout: float,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command to completion and capture its text output.

    Raises:
        subprocess.TimeoutExpired: The command ran longer than `timeout` seconds.
        subprocess.CalledProcessError: `check` is True and the command exits non-zero.
    """
    return subprocess.run(
        list(args),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        check=check,
        timeout=timeout,
    )
