"""HTTP health probe polling and readiness gating for API Gateway."""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request

from .colors import CYAN, GREEN, RED, RESET

__all__ = ["check_health", "wait_for_gateway", "wait_for_gateway_healthy"]


def check_health(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if the API Gateway health probe responds with HTTP 200."""
    endpoints = [
        f"http://{host}:{port}/api/v1/health",
        f"http://{host}:{port}/healthz",
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Runefoble-Dev-Orchestrator"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, ConnectionRefusedError, OSError):
            continue
    return False


def wait_for_gateway_healthy(
    host: str,
    port: int,
    gateway_proc: subprocess.Popen | None = None,
    timeout: float = 30.0,
    poll_interval: float = 0.25,
) -> bool:
    """Poll the API Gateway health endpoint until ready or timeout expires."""
    start_time = time.monotonic()
    print(
        f"{CYAN}[dev-orchestrator]{RESET} Waiting for API Gateway at http://{host}:{port}...",
        flush=True,
    )

    while time.monotonic() - start_time < timeout:
        if gateway_proc and gateway_proc.poll() is not None:
            print(
                f"{RED}[dev-orchestrator] Error: API Gateway exited prematurely with code {gateway_proc.returncode}.{RESET}",
                file=sys.stderr,
                flush=True,
            )
            return False

        if check_health(host, port, timeout=poll_interval):
            elapsed = time.monotonic() - start_time
            print(
                f"{GREEN}[dev-orchestrator] API Gateway is healthy and ready! ({elapsed:.2f}s){RESET}",
                flush=True,
            )
            return True

        time.sleep(poll_interval)

    print(
        f"{RED}[dev-orchestrator] Timed out waiting for API Gateway after {timeout:.1f}s.{RESET}",
        file=sys.stderr,
        flush=True,
    )
    return False


wait_for_gateway = wait_for_gateway_healthy
