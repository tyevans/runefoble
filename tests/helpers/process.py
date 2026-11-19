"""Run external commands from tests. Every call has a time limit.

`subprocess.run` without a timeout can block a test run forever when a child process hangs.
`run_command` makes the limit a required keyword, so no caller can omit it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

# The service credential is refused at import time unless set. Child processes that test the
# refusal must start without it, so this helper removes it before applying any override.
SERVICE_CREDENTIAL_ENV = "RUNEFOBLE_SERVICE_CREDENTIAL"


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


def run_python_child(
    code: str,
    env_overrides: Mapping[str, str | None] | None = None,
    cwd: Path | str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `python -c <code>` in a child process without the service credential.

    An override with the value None is ignored. Any other value sets that variable.
    """
    env = {key: value for key, value in os.environ.items() if key != SERVICE_CREDENTIAL_ENV}
    for key, value in (env_overrides or {}).items():
        if value is not None:
            env[key] = value
    return run_command([sys.executable, "-c", code], cwd=cwd, env=env, timeout=120)
