"""Start the local environment in order, gate on gateway health, then monitor until one child exits.

Governed by ADR-0004, ADR-0010, and ADR-0013. Part of TASK-0352.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from argparse import Namespace

from .colors import BOLD, CYAN, GREEN, MAGENTA, RED, RESET, YELLOW
from .health import wait_for_gateway
from .port_forwards import ensure_redis_available, ensure_spicedb_available
from .ports import redis_endpoint
from .runner import register_child, terminate_processes
from .stack import print_banner, start_frontend, start_gateway, start_worker


def run_orchestrator(args: Namespace) -> int:
    """Run the local environment. Every child stops on every exit path, including errors."""
    processes: list[subprocess.Popen] = []
    try:
        return supervise(args, processes)
    finally:
        terminate_processes(processes)


def supervise(args: Namespace, processes: list[subprocess.Popen]) -> int:
    """Start the children and monitor them. The caller stops them, so every return path is covered."""
    signal.signal(signal.SIGINT, _exit_on_signal)
    signal.signal(signal.SIGTERM, _exit_on_signal)

    spicedb_host = str(args.spicedb_host)
    spicedb_port = int(args.spicedb_port)

    # 0. Ensure SpiceDB is accessible (auto-forwarding from K8s if needed)
    spicedb_proc = ensure_spicedb_available(host=spicedb_host, port=spicedb_port)
    if spicedb_proc is not None:
        register_child(processes, spicedb_proc, "spicedb-pf", YELLOW)

    # 0b. Require Redis. The gateway fails start-up without it.
    redis_host, redis_port = redis_endpoint(os.environ)
    try:
        redis_proc = ensure_redis_available(redis_host, redis_port)
    except RuntimeError as exc:
        print(f"{RED}[dev-orchestrator] {exc}{RESET}", flush=True)
        return 1
    if redis_proc is not None:
        register_child(processes, redis_proc, "redis-pf", YELLOW)

    print_banner(args, spicedb_host, spicedb_port)

    # 1. Start API Gateway
    gateway_proc = start_gateway(args, spicedb_host, spicedb_port)
    register_child(processes, gateway_proc, "gateway", CYAN)

    # 2. Optionally start AI Inference Worker
    if args.worker:
        register_child(processes, start_worker(), "worker", MAGENTA)

    # 3. Wait for API Gateway health check
    healthy = wait_for_gateway(
        host=args.gateway_host,
        port=args.gateway_port,
        gateway_proc=gateway_proc,
        timeout=args.timeout,
    )
    if not healthy:
        return 1

    # 4. Start Vite Frontend
    if not args.no_frontend:
        register_child(processes, start_frontend(args), "frontend", GREEN)
        print(
            f"{GREEN}{BOLD}[dev-orchestrator] Ready! App Shell available at http://localhost:{args.frontend_port}{RESET}\n",
            flush=True,
        )

    # 5. Monitor processes until exit
    return monitor(processes)


def monitor(processes: list[subprocess.Popen]) -> int:
    """Return the exit code of the first child that stops. Return 0 on a keyboard interrupt."""
    try:
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(
                        f"{YELLOW}[dev-orchestrator] Process {p.pid} terminated with code {p.returncode}. Stopping environment.{RESET}",
                        flush=True,
                    )
                    return p.returncode
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0


def _exit_on_signal(signum: int, _frame: object) -> None:
    # SystemExit unwinds to run_orchestrator, which stops the children.
    sys.exit(0)
