"""Child process supervision: spawn in a process group, stream output, and tear down."""

from __future__ import annotations

import contextlib
import ctypes
import functools
import os
import signal
import subprocess
import sys
import threading
import time

from .colors import GREEN, RESET, YELLOW

PR_SET_PDEATHSIG = 1
_LIBC = ctypes.CDLL(None, use_errno=True) if sys.platform.startswith("linux") else None


def _die_with_parent(libc: ctypes.CDLL, parent_pid: int) -> None:
    """Forked-child hook: the kernel sends SIGTERM to this child when the dev server dies."""
    if libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM) != 0:
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")
    if os.getppid() != parent_pid:  # The dev server died before the signal was armed.
        os.kill(os.getpid(), signal.SIGTERM)


def spawn_child(
    cmd: list[str], *, cwd: str | None = None, env: dict[str, str] | None = None
) -> subprocess.Popen:
    """Start a child in its own process group, with output piped to the orchestrator."""
    preexec_fn = None
    if _LIBC is not None:
        preexec_fn = functools.partial(_die_with_parent, _LIBC, os.getpid())
    return subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        preexec_fn=preexec_fn,
    )


def pipe_output(proc: subprocess.Popen, prefix: str, color: str) -> None:
    """Pipe child process stdout/stderr with colored prefix in real-time."""
    if not proc.stdout:
        return

    try:
        for line in iter(proc.stdout.readline, b""):
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            print(f"{color}[{prefix}]{RESET} {text}", flush=True)
    except Exception:
        pass


def register_child(
    processes: list[subprocess.Popen], proc: subprocess.Popen, label: str, color: str
) -> None:
    """Track a running child for teardown and stream its output under a colored label."""
    processes.append(proc)
    threading.Thread(target=pipe_output, args=(proc, label, color), daemon=True).start()


def terminate_processes(processes: list[subprocess.Popen]) -> None:
    """Stop every child that is still running, and its process group. Safe to call more than once."""
    live = [p for p in processes if p.poll() is None]
    if not live:
        return
    print(
        f"\n{YELLOW}[dev-orchestrator] Shutting down all development processes...{RESET}",
        flush=True,
    )
    for p in live:
        _signal_group(p, signal.SIGTERM)

    # Give processes a graceful shutdown window
    deadline = time.monotonic() + 3.0
    for p in live:
        while time.monotonic() < deadline and p.poll() is None:
            time.sleep(0.1)

    # Force kill any lingering processes
    for p in live:
        if p.poll() is None:
            _signal_group(p, signal.SIGKILL)
    print(f"{GREEN}[dev-orchestrator] All processes cleanly stopped.{RESET}", flush=True)


def _signal_group(proc: subprocess.Popen, signum: int) -> None:
    """Send a signal to the child's process group. Fall back to the child alone."""
    try:
        os.killpg(proc.pid, signum)
    except ProcessLookupError:
        return  # The group has no members left.
    except OSError:
        with contextlib.suppress(OSError):
            proc.send_signal(signum)
