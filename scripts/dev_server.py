#!/usr/bin/env python3
"""Runefoble Unified Local Development Orchestrator.

Starts the API Gateway, optional background inference worker, and hot-reloading
Vite frontend concurrently with health check gating and clean signal handling.

Governed by ADR-0004, ADR-0010, and ADR-0013. Part of TASK-0352.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import functools
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent

# ANSI Colors for developer terminal logging
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"
RESET = "\033[0m"


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


DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def redis_endpoint(env: dict[str, str] | os._Environ[str]) -> tuple[str, int]:
    """Return the Redis host and port that services will use, from the same env as the gateway."""
    url = env.get("RUNEFOBLE_REDIS_URL") or env.get("REDIS_URL") or DEFAULT_REDIS_URL
    parsed = urlparse(url)
    return parsed.hostname or "localhost", parsed.port or 6379


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
        "--spicedb-port",
        type=int,
        default=int(os.environ.get("SPICEDB_PORT", "50051")),
        help="Port for SpiceDB Zanzibar gRPC (default: 50051)",
    )
    parser.add_argument(
        "--spicedb-host",
        type=str,
        default=os.environ.get("SPICEDB_HOST", "127.0.0.1"),
        help="Host for SpiceDB Zanzibar gRPC (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("GATEWAY_HEALTH_TIMEOUT", "30.0")),
        help="Timeout in seconds for Gateway readiness probe (default: 30.0)",
    )
    return parser.parse_args(args)


def run_orchestrator(args: argparse.Namespace) -> int:
    """Run the local environment. Every child stops on every exit path, including errors."""
    processes: list[subprocess.Popen] = []
    try:
        return supervise(args, processes)
    finally:
        terminate_processes(processes)


def supervise(args: argparse.Namespace, processes: list[subprocess.Popen]) -> int:
    """Start the children and monitor them. The caller stops them, so every return path is covered."""
    threads: list[threading.Thread] = []

    def sig_handler(signum: int, _frame: object) -> None:
        # SystemExit unwinds to run_orchestrator, which stops the children.
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    spicedb_host = str(args.spicedb_host)
    spicedb_port = int(args.spicedb_port)

    # 0. Ensure SpiceDB is accessible (auto-forwarding from K8s if needed)
    spicedb_proc = ensure_spicedb_available(host=spicedb_host, port=spicedb_port)
    if spicedb_proc is not None:
        processes.append(spicedb_proc)
        t_spicedb = threading.Thread(
            target=pipe_output, args=(spicedb_proc, "spicedb-pf", YELLOW), daemon=True
        )
        t_spicedb.start()
        threads.append(t_spicedb)

    # 0b. Require Redis. The gateway fails start-up without it.
    redis_host, redis_port = redis_endpoint(os.environ)
    try:
        redis_proc = ensure_redis_available(redis_host, redis_port)
    except RuntimeError as exc:
        print(f"{RED}[dev-orchestrator] {exc}{RESET}", flush=True)
        return 1
    if redis_proc is not None:
        processes.append(redis_proc)
        t_redis = threading.Thread(
            target=pipe_output, args=(redis_proc, "redis-pf", YELLOW), daemon=True
        )
        t_redis.start()
        threads.append(t_redis)

    print(f"{BOLD}{MAGENTA}======================================================{RESET}")
    print(f"{BOLD}{MAGENTA}       Runefoble Local Development Environment        {RESET}")
    print(f"{BOLD}{MAGENTA}======================================================{RESET}")
    print(f"{CYAN}  * API Gateway:{RESET}     http://{args.gateway_host}:{args.gateway_port}")
    print(f"{CYAN}  * SpiceDB gRPC:{RESET}    {spicedb_host}:{spicedb_port}")
    if not args.no_frontend:
        print(f"{CYAN}  * Vite Frontend:{RESET}   http://localhost:{args.frontend_port}")
    if args.worker:
        print(f"{CYAN}  * Inference Worker:{RESET} active")
    print(f"{BOLD}{MAGENTA}------------------------------------------------------{RESET}\n")

    # 1. Start API Gateway
    gateway_env = os.environ.copy()
    gateway_env["GATEWAY_PORT"] = str(args.gateway_port)
    gateway_env["GATEWAY_HOST"] = str(args.gateway_host)
    if "RUNEFOBLE_SPICEDB_ENDPOINT" not in gateway_env:
        gateway_env["RUNEFOBLE_SPICEDB_ENDPOINT"] = f"{spicedb_host}:{spicedb_port}"
    if "SPICEDB_ENDPOINT" not in gateway_env:
        gateway_env["SPICEDB_ENDPOINT"] = f"{spicedb_host}:{spicedb_port}"

    gateway_cmd = (
        ["uv", "run", "python", "gateway/api/src/gateway_api/main.py"]
        if shutil.which("uv")
        else [sys.executable, "gateway/api/src/gateway_api/main.py"]
    )

    gateway_proc = spawn_child(gateway_cmd, cwd=str(REPO_ROOT), env=gateway_env)
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
        worker_proc = spawn_child(worker_cmd, cwd=str(REPO_ROOT))
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
        return 1

    # 4. Start Vite Frontend
    if not args.no_frontend:
        frontend_env = os.environ.copy()
        frontend_env["CHOKIDAR_USEPOLLING"] = "true"
        frontend_env["GATEWAY_API_URL"] = f"http://{args.gateway_host}:{args.gateway_port}"
        frontend_env["GATEWAY_WS_URL"] = f"ws://{args.gateway_host}:{args.gateway_port}"

        vite_cmd = ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", str(args.frontend_port)]

        frontend_proc = spawn_child(vite_cmd, cwd=str(REPO_ROOT / "frontend"), env=frontend_env)
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
                    return p.returncode
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0


def main() -> None:
    """Entry point."""
    args = parse_args()
    sys.exit(run_orchestrator(args))


if __name__ == "__main__":
    main()
