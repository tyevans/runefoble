"""Start or stop the campaign_lore service for the gateway-down e2e journey (TASK-0695).

`up` starts campaign_lore on its port with the caller's environment and records the process group in `.e2e/campaign_lore.pid`.
`down` stops only the process group that `up` recorded. It never stops a process it did not start.
A port that another process already serves is refused, so the journey fails loudly.
"""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

PORT = 8006
ROOT = Path(__file__).resolve().parent.parent
PID_FILE = ROOT / ".e2e" / "campaign_lore.pid"


def _listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _wait(predicate, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.25)
    return predicate()


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def up() -> int:
    if PID_FILE.exists():
        return (
            0
            if _listening()
            else _fail("Stale campaign_lore pid file. Run make e2e-lore-down first.")
        )
    if _listening():
        return _fail(
            f"Port {PORT} is served by a process this script did not start. Stop it first."
        )
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "campaign_lore.main:app", "--port", str(PORT)],
        cwd=ROOT,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PID_FILE.write_text(str(proc.pid))
    if not _wait(lambda: _listening() or proc.poll() is not None, 60) or proc.poll() is not None:
        PID_FILE.unlink(missing_ok=True)
        return _fail("campaign_lore did not start. Export its settings in the caller environment.")
    return 0


def down() -> int:
    if not PID_FILE.exists():
        return _fail("No campaign_lore process was started by make e2e-lore-up.")
    pgid = int(PID_FILE.read_text())
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pgid, signal.SIGTERM)
    if not _wait(lambda: not _listening(), 15):
        return _fail("campaign_lore is still listening after SIGTERM.")
    PID_FILE.unlink()
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "up":
        sys.exit(up())
    if command == "down":
        sys.exit(down())
    sys.exit(_fail("Usage: e2e_lore_fault.py up|down"))
