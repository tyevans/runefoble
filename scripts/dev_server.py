#!/usr/bin/env python3
"""Runefoble Comprehensive Local Development Orchestrator.

Starts API Gateway, optional background inference worker, and hot-reloading
Vite frontend concurrently with health check gating and clean process termination.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence

# Color helpers for terminal logging
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def log(prefix: str, message: str, color: str = CYAN) -> None:
    """Print formatted message with service prefix."""
    print(f"{color}[{prefix}]{RESET} {message}", flush=True)


def wait_for_health(
    url: str,
    timeout: float = 30.0,
    interval: float = 0.5,
    proc: subprocess.Popen | None = None,
) -> bool:
    """Poll health URL until it responds with HTTP 200 or timeout expires."""
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        if proc is not None and proc.poll() is not None:
            log("health-check", f"Process exited prematurely with code {proc.returncode}", RED)
            return False

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Runefoble-Dev-Orchestrator"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            pass

        time.sleep(interval)

    return False


def terminate_processes(processes: Sequence[subprocess.Popen], timeout: float = 5.0) -> None:
    """Cleanly terminate child processes with SIGTERM, escalating to SIGKILL if necessary."""
    for proc in processes:
        if proc.poll() is None:
            with contextlib.suppress(OSError):
                proc.send_signal(signal.SIGINT)

    # Wait for grace period
    deadline = time.monotonic() + timeout
    for proc in processes:
        remaining = max(0.1, deadline - time.monotonic())
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=remaining)

    # Force kill any remaining processes
    for proc in processes:
        if proc.poll() is None:
            with contextlib.suppress(OSError):
                proc.kill()
                proc.wait(timeout=1.0)


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Runefoble unified local development server orchestrator."
    )
    parser.add_argument(
        "--gateway-port",
        type=int,
        default=int(os.environ.get("GATEWAY_PORT", "8000")),
        help="Port for Runefoble API Gateway (default: 8000)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=int(os.environ.get("FRONTEND_PORT", "5173")),
        help="Port for Vite frontend dev server (default: 5173)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("RUNEFOBLE_DEV_HOST", "127.0.0.1"),
        help="Host address for health checks and service binds (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--health-timeout",
        type=float,
        default=float(os.environ.get("RUNEFOBLE_HEALTH_TIMEOUT", "30.0")),
        help="Maximum seconds to wait for gateway health check (default: 30.0)",
    )
    parser.add_argument(
        "--with-worker",
        action="store_true",
        default=bool(os.environ.get("RUNEFOBLE_DEV_WITH_WORKER", "")),
        help="Start background AI inference worker concurrently",
    )
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Skip starting the Vite frontend development server",
    )
    parser.add_argument(
        "--no-gateway",
        action="store_true",
        help="Skip starting the API Gateway",
    )
    return parser.parse_args(args)


def run_dev_server(args: argparse.Namespace) -> int:
    """Orchestrate API Gateway, background worker, and Vite frontend."""
    processes: list[subprocess.Popen] = []
    interrupted = False

    def sig_handler(signum: int, _frame: object) -> None:
        nonlocal interrupted
        interrupted = True
        log("dev-server", f"Received signal {signum}, shutting down child processes...", YELLOW)
        terminate_processes(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gateway_proc: subprocess.Popen | None = None
    worker_proc: subprocess.Popen | None = None
    frontend_proc: subprocess.Popen | None = None

    try:
        # 1. Start Background Inference Worker if requested
        if args.with_worker:
            log("worker", "Starting Runefoble AI inference worker...")
            worker_cmd = ["uv", "run", "runefoble-inference-worker"]
            worker_proc = subprocess.Popen(worker_cmd, cwd=repo_root)
            processes.append(worker_proc)

        # 2. Start API Gateway
        if not args.no_gateway:
            log("gateway", f"Starting Runefoble API Gateway on port {args.gateway_port}...")
            env = os.environ.copy()
            env["PORT"] = str(args.gateway_port)
            gateway_cmd = [
                "uv",
                "run",
                "python",
                "gateway/api/src/gateway_api/main.py",
            ]
            gateway_proc = subprocess.Popen(gateway_cmd, cwd=repo_root, env=env)
            processes.append(gateway_proc)

            # Wait for Gateway Health Check
            health_url = f"http://{args.host}:{args.gateway_port}/healthz"
            log(
                "gateway",
                f"Waiting for Gateway health check at {health_url} "
                f"(timeout={args.health_timeout}s)...",
            )
            healthy = wait_for_health(
                health_url,
                timeout=args.health_timeout,
                proc=gateway_proc,
            )

            if not healthy:
                log("gateway", "Health check failed or timed out. Aborting.", RED)
                terminate_processes(processes)
                return 1

            log("gateway", "API Gateway is healthy and ready for traffic.", GREEN)

        # 3. Start Vite Frontend Server
        if not args.no_frontend:
            log(
                "frontend",
                f"Starting Vite frontend dev server on port {args.frontend_port}...",
            )
            frontend_dir = os.path.join(repo_root, "frontend")
            env = os.environ.copy()
            env["CHOKIDAR_USEPOLLING"] = "true"
            env["GATEWAY_API_URL"] = f"http://{args.host}:{args.gateway_port}"
            frontend_cmd = [
                "pnpm",
                "run",
                "dev",
                "--port",
                str(args.frontend_port),
            ]
            frontend_proc = subprocess.Popen(frontend_cmd, cwd=frontend_dir, env=env)
            processes.append(frontend_proc)

        log("dev-server", "Local development environment is live.", GREEN)
        log("dev-server", f"Frontend UI: http://localhost:{args.frontend_port}", CYAN)
        log("dev-server", f"API Gateway: http://localhost:{args.gateway_port}/docs", CYAN)
        log("dev-server", "Press Ctrl+C to terminate all services.", YELLOW)

        # Monitor processes
        while not interrupted:
            time.sleep(0.5)
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    log("dev-server", f"Process exited with code {code}. Shutting down...", YELLOW)
                    return code

        return 0

    except KeyboardInterrupt:
        log("dev-server", "KeyboardInterrupt detected, terminating...", YELLOW)
        return 0
    finally:
        terminate_processes(processes)


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    code = run_dev_server(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
