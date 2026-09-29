"""Network port probing and SpiceDB forwarding utilities."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import time

from .colors import CYAN, GREEN, RESET, YELLOW

__all__ = ["ensure_spicedb_available", "is_port_open"]


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a TCP port is open and accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


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
                pf_proc = subprocess.Popen(
                    ["kubectl", "port-forward", "svc/spicedb", f"{port}:{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
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
