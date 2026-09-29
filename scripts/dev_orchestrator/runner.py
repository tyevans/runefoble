"""Subprocess lifecycle management, stream output piping, and signal handling."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .colors import CYAN, GREEN, RESET, YELLOW

__all__ = ["DevProcessManager", "DevService", "pipe_output", "pipe_stream", "terminate_processes"]


@dataclass
class DevService:
    """Specification of a development service subprocess to launch and monitor."""

    name: str
    cmd: list[str]
    cwd: str | Path
    env: dict[str, str] | None = None
    color: str = CYAN
    proc: subprocess.Popen | None = None


def pipe_stream(proc: subprocess.Popen, prefix: str, color: str) -> None:
    """Pipe child process stdout/stderr with colored prefix in real-time."""
    if proc.stdout:
        with contextlib.suppress(Exception):
            for line in iter(proc.stdout.readline, b""):
                if text := line.decode("utf-8", errors="replace").rstrip():
                    print(f"{color}[{prefix}]{RESET} {text}", flush=True)


pipe_output = pipe_stream


def terminate_processes(processes: Sequence[subprocess.Popen]) -> None:
    """Cleanly terminate child processes and their process groups."""
    print(
        f"\n{YELLOW}[dev-orchestrator] Shutting down all development processes...{RESET}",
        flush=True,
    )
    for p in processes:
        if p.poll() is None:
            with contextlib.suppress(OSError):
                os.killpg(p.pid, signal.SIGTERM)

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and any(p.poll() is None for p in processes):
        time.sleep(0.1)

    for p in processes:
        if p.poll() is None:
            with contextlib.suppress(OSError):
                os.killpg(p.pid, signal.SIGKILL)

    print(f"{GREEN}[dev-orchestrator] All processes cleanly stopped.{RESET}", flush=True)


class DevProcessManager:
    """Manages subprocess lifecycles, signal dispatch, and stream piping."""

    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []
        self.threads: list[threading.Thread] = []
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda _s, _f: (self.terminate_all(), sys.exit(0)))

    def register(
        self, proc: subprocess.Popen, prefix: str, color: str = YELLOW
    ) -> subprocess.Popen:
        """Register an existing process and start streaming its output."""
        self.processes.append(proc)
        t = threading.Thread(target=pipe_stream, args=(proc, prefix, color), daemon=True)
        t.start()
        self.threads.append(t)
        return proc

    def launch(self, service: DevService) -> subprocess.Popen:
        """Launch a service subprocess and attach output streaming."""
        proc = subprocess.Popen(
            service.cmd,
            cwd=str(service.cwd),
            env=service.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        service.proc = proc
        return self.register(proc, service.name, service.color)

    def terminate_all(self) -> None:
        """Cleanly terminate all managed processes."""
        terminate_processes(self.processes)

    def monitor(self) -> int:
        """Monitor running processes until one exits or interrupted."""
        try:
            while True:
                for p in self.processes:
                    if p.poll() is not None:
                        print(
                            f"{YELLOW}[dev-orchestrator] Process {p.pid} terminated with code "
                            f"{p.returncode}. Stopping environment.{RESET}",
                            flush=True,
                        )
                        self.terminate_all()
                        return p.returncode
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.terminate_all()
            return 0
