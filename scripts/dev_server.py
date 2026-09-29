#!/usr/bin/env python3
"""Runefoble Unified Local Development Orchestrator.

Starts the API Gateway, optional background inference worker, and hot-reloading
Vite frontend concurrently with health check gating and clean signal handling.

Governed by ADR-0004, ADR-0010, and ADR-0013. Part of TASK-0352.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ANSI Colors for developer terminal logging
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"
RESET = "\033[0m"


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


def wait_for_gateway(
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


def terminate_processes(processes: list[subprocess.Popen]) -> None:
    """Cleanly terminate child processes and their process groups."""
    print(
        f"\n{YELLOW}[dev-orchestrator] Shutting down all development processes...{RESET}",
        flush=True,
    )
    for p in processes:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                with contextlib.suppress(OSError):
                    p.terminate()

    # Give processes a graceful shutdown window
    deadline = time.monotonic() + 3.0
    for p in processes:
        while time.monotonic() < deadline and p.poll() is None:
            time.sleep(0.1)

    # Force kill any lingering processes
    for p in processes:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                with contextlib.suppress(OSError):
                    p.kill()
    print(f"{GREEN}[dev-orchestrator] All processes cleanly stopped.{RESET}", flush=True)


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for local dev orchestrator."""
    parser = argparse.ArgumentParser(
        description="Runefoble local development orchestrator (make dev)",
    )
    parser.add_argument(
        "--gateway-port",
        type=int,
        default=int(os.environ.get("GATEWAY_PORT", "8000")),
        help="Port for Runefoble API Gateway (default: 8000)",
    )
    parser.add_argument(
        "--gateway-host",
        type=str,
        default=os.environ.get("GATEWAY_HOST", "127.0.0.1"),
        help="Host for Runefoble API Gateway (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=int(os.environ.get("FRONTEND_PORT", "5173")),
        help="Port for Vite Frontend dev server (default: 5173)",
    )
    parser.add_argument(
        "--worker",
        "--with-worker",
        action="store_true",
        default=os.environ.get("RUNEFOBLE_DEV_WORKER", "").lower() in ("true", "1", "yes"),
        help="Start background AI inference worker",
    )
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        default=False,
        help="Skip starting the Vite frontend",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("GATEWAY_HEALTH_TIMEOUT", "30.0")),
        help="Timeout in seconds for Gateway readiness probe (default: 30.0)",
    )
    return parser.parse_args(args)


def run_orchestrator(args: argparse.Namespace) -> int:
    """Main execution orchestrator."""
    processes: list[subprocess.Popen] = []
    threads: list[threading.Thread] = []

    def sig_handler(signum: int, _frame: object) -> None:
        terminate_processes(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    print(f"{BOLD}{MAGENTA}======================================================{RESET}")
    print(f"{BOLD}{MAGENTA}       Runefoble Local Development Environment        {RESET}")
    print(f"{BOLD}{MAGENTA}======================================================{RESET}")
    print(f"{CYAN}  * API Gateway:{RESET}     http://{args.gateway_host}:{args.gateway_port}")
    if not args.no_frontend:
        print(f"{CYAN}  * Vite Frontend:{RESET}   http://localhost:{args.frontend_port}")
    if args.worker:
        print(f"{CYAN}  * Inference Worker:{RESET} active")
    print(f"{BOLD}{MAGENTA}------------------------------------------------------{RESET}\n")

    # 1. Start API Gateway
    gateway_env = os.environ.copy()
    gateway_env["GATEWAY_PORT"] = str(args.gateway_port)
    gateway_env["GATEWAY_HOST"] = str(args.gateway_host)

    gateway_cmd = (
        ["uv", "run", "python", "gateway/api/src/gateway_api/main.py"]
        if shutil.which("uv")
        else [sys.executable, "gateway/api/src/gateway_api/main.py"]
    )

    gateway_proc = subprocess.Popen(
        gateway_cmd,
        cwd=str(REPO_ROOT),
        env=gateway_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    processes.append(gateway_proc)

    t_gateway = threading.Thread(
        target=pipe_output, args=(gateway_proc, "gateway", CYAN), daemon=True
    )
    t_gateway.start()
    threads.append(t_gateway)

    # 2. Optionally start AI Inference Worker
    if args.worker:
        worker_cmd = (
            ["uv", "run", "runefoble-inference-worker"]
            if shutil.which("uv")
            else ["runefoble-inference-worker"]
        )
        worker_proc = subprocess.Popen(
            worker_cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        processes.append(worker_proc)
        t_worker = threading.Thread(
            target=pipe_output, args=(worker_proc, "worker", MAGENTA), daemon=True
        )
        t_worker.start()
        threads.append(t_worker)

    # 3. Wait for API Gateway health check
    healthy = wait_for_gateway(
        host=args.gateway_host,
        port=args.gateway_port,
        gateway_proc=gateway_proc,
        timeout=args.timeout,
    )

    if not healthy:
        terminate_processes(processes)
        return 1

    # 4. Start Vite Frontend
    if not args.no_frontend:
        frontend_env = os.environ.copy()
        frontend_env["CHOKIDAR_USEPOLLING"] = "true"
        frontend_env["GATEWAY_API_URL"] = f"http://{args.gateway_host}:{args.gateway_port}"
        frontend_env["GATEWAY_WS_URL"] = f"ws://{args.gateway_host}:{args.gateway_port}"

        vite_cmd = ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", str(args.frontend_port)]

        frontend_proc = subprocess.Popen(
            vite_cmd,
            cwd=str(REPO_ROOT / "frontend"),
            env=frontend_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        processes.append(frontend_proc)

        t_frontend = threading.Thread(
            target=pipe_output, args=(frontend_proc, "frontend", GREEN), daemon=True
        )
        t_frontend.start()
        threads.append(t_frontend)

        print(
            f"{GREEN}{BOLD}[dev-orchestrator] Ready! App Shell available at http://localhost:{args.frontend_port}{RESET}\n",
            flush=True,
        )

    # 5. Monitor processes until exit
    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(
                        f"{YELLOW}[dev-orchestrator] Process {p.pid} terminated with code {p.returncode}. Stopping environment.{RESET}",
                        flush=True,
                    )
                    terminate_processes(processes)
                    return p.returncode
            time.sleep(0.5)
    except KeyboardInterrupt:
        terminate_processes(processes)
        return 0


def main() -> None:
    """Entry point."""
    args = parse_args()
    sys.exit(run_orchestrator(args))


if __name__ == "__main__":
    main()
