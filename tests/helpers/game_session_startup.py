"""Start the real game session app in a child Python process (TASK-0755).

The app builds its container in the lifespan (ADR-0021 D6). So a start-up check runs the
lifespan of `game_session.main:app`, as uvicorn does, and does not stop at the import.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from tests.helpers.process import run_command

STARTED_MARKER = "game_session started"

_STARTUP_CODE = (
    "import asyncio\n"
    "from game_session.main import app\n"
    "async def start():\n"
    "    async with app.router.lifespan_context(app):\n"
    f"        print({STARTED_MARKER!r})\n"
    "asyncio.run(start())\n"
)


def start_game_session(
    env_overrides: Mapping[str, str | None], cwd: Path, *, base_env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the app lifespan once in a child process with the environment changes applied.

    A value of None removes the variable. The child exits after the lifespan starts and stops.
    """
    env = dict(os.environ if base_env is None else base_env)
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return run_command(
        [sys.executable, "-c", _STARTUP_CODE], cwd=cwd, env=env, timeout=120, check=False
    )


__all__ = ["STARTED_MARKER", "start_game_session"]
