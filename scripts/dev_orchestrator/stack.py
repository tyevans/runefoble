"""The services that `make dev` starts: banner, API Gateway, AI worker, and Vite frontend."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

from .colors import BOLD, CYAN, MAGENTA, RESET
from .runner import spawn_child

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def print_banner(args: Namespace, spicedb_host: str, spicedb_port: int) -> None:
    """Print the endpoints of the local environment before the services start."""
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


def start_gateway(args: Namespace, spicedb_host: str, spicedb_port: int) -> subprocess.Popen:
    """Start the API Gateway. It reads its settings from the environment."""
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
    return spawn_child(gateway_cmd, cwd=str(REPO_ROOT), env=gateway_env)


def start_worker() -> subprocess.Popen:
    """Start the background AI inference worker."""
    worker_cmd = (
        ["uv", "run", "runefoble-inference-worker"]
        if shutil.which("uv")
        else ["runefoble-inference-worker"]
    )
    return spawn_child(worker_cmd, cwd=str(REPO_ROOT))


def start_frontend(args: Namespace) -> subprocess.Popen:
    """Start the hot-reloading Vite dev server, pointed at the gateway."""
    frontend_env = os.environ.copy()
    frontend_env["CHOKIDAR_USEPOLLING"] = "true"
    frontend_env["GATEWAY_API_URL"] = f"http://{args.gateway_host}:{args.gateway_port}"
    frontend_env["GATEWAY_WS_URL"] = f"ws://{args.gateway_host}:{args.gateway_port}"

    vite_cmd = ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", str(args.frontend_port)]
    return spawn_child(vite_cmd, cwd=str(REPO_ROOT / "frontend"), env=frontend_env)
