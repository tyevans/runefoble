"""Kubectl port-forward fallbacks for SpiceDB and Redis when the Kind cluster hosts them."""

from __future__ import annotations

import os
import shutil
import subprocess
import time

from .colors import CYAN, GREEN, RESET, YELLOW
from .ports import is_port_open
from .runner import spawn_child, terminate_processes


def ensure_spicedb_available(
    host: str = "127.0.0.1", port: int = 50051, timeout: float = 5.0
) -> subprocess.Popen | None:
    """Ensure SpiceDB is accessible on host:port, auto-forwarding from Kind/K8s if needed."""
    if (
        os.environ.get("SPICEDB_ENDPOINT") == "mock"
        or os.environ.get("RUNEFOBLE_SPICEDB_ENDPOINT") == "mock"
    ):
        return None

    if is_port_open(host, port):
        return None

    if shutil.which("kubectl"):
        try:
            check = subprocess.run(
                ["kubectl", "get", "svc", "spicedb"],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if check.returncode == 0:
                print(
                    f"{CYAN}[dev-orchestrator]{RESET} Establishing SpiceDB port-forward (svc/spicedb:{port})...",
                    flush=True,
                )
                pf_proc = spawn_child(["kubectl", "port-forward", "svc/spicedb", f"{port}:{port}"])
                start_time = time.monotonic()
                while time.monotonic() - start_time < timeout:
                    if is_port_open(host, port):
                        print(
                            f"{GREEN}[dev-orchestrator] SpiceDB port-forward established at {host}:{port}!{RESET}",
                            flush=True,
                        )
                        return pf_proc
                    if pf_proc.poll() is not None:
                        break
                    time.sleep(0.2)
                return pf_proc
        except Exception:
            pass

    print(
        f"{YELLOW}[dev-orchestrator] Warning: SpiceDB not reachable at {host}:{port}. "
        f"Make sure SpiceDB is running or port-forwarded.{RESET}",
        flush=True,
    )
    return None


def ensure_redis_available(host: str, port: int, timeout: float = 5.0) -> subprocess.Popen | None:
    """Require a reachable Redis. Services refuse to start without it (ADR-0015).

    Return a kubectl port-forward process when the Kind cluster supplies Redis. Return None when
    Redis already answers. Raise RuntimeError when no Redis can be reached.
    """
    if is_port_open(host, port):
        return None
    if host in ("localhost", "127.0.0.1") and shutil.which("kubectl"):
        check = subprocess.run(
            ["kubectl", "get", "svc", "runefoble-redis"],
            capture_output=True,
            text=True,
            timeout=3.0,
        )
        if check.returncode == 0:
            print(
                f"{CYAN}[dev-orchestrator]{RESET} Establishing Redis port-forward "
                f"(svc/runefoble-redis:{port})...",
                flush=True,
            )
            pf_proc = spawn_child(
                ["kubectl", "port-forward", "svc/runefoble-redis", f"{port}:6379"]
            )
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and pf_proc.poll() is None:
                if is_port_open(host, port):
                    return pf_proc
                time.sleep(0.2)
            terminate_processes([pf_proc])
    raise RuntimeError(
        f"Redis is not reachable at {host}:{port}. Start the Kind stack (make cluster-up) or "
        "set RUNEFOBLE_REDIS_URL to a running Redis."
    )
