#!/usr/bin/env python3
"""Runefoble Unified Local Development Orchestrator CLI Driver.

Governed by ADR-0003, ADR-0010, and ADR-0013. Part of TASK-0434.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.dev_orchestrator import (  # noqa: E402
    CYAN,
    GREEN,
    MAGENTA,
    DevProcessManager,
    DevService,
    check_health,
    ensure_spicedb_available,
    is_port_open,
    print_banner,
    terminate_processes,
    wait_for_gateway,
)

__all__ = ["check_health", "is_port_open", "terminate_processes"]


def parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for local dev orchestrator."""
    p = argparse.ArgumentParser(description="Runefoble local development orchestrator (make dev)")
    g = os.getenv
    p.add_argument("--gateway-port", type=int, default=int(g("GATEWAY_PORT", 8000)))
    p.add_argument("--gateway-host", default=g("GATEWAY_HOST", "127.0.0.1"))
    p.add_argument("--frontend-port", type=int, default=int(g("FRONTEND_PORT", 5173)))
    p.add_argument("--spicedb-port", type=int, default=int(g("SPICEDB_PORT", 50051)))
    p.add_argument("--spicedb-host", default=g("SPICEDB_HOST", "127.0.0.1"))
    to = float(g("GATEWAY_HEALTH_TIMEOUT", 30.0))
    p.add_argument("--timeout", type=float, default=to)
    w = g("RUNEFOBLE_DEV_WORKER", "").lower() in ("true", "1", "yes")
    p.add_argument("--worker", "--with-worker", action="store_true", default=w)
    p.add_argument("--no-frontend", action="store_true", default=False)
    return p.parse_args(args)


def run_orchestrator(args: argparse.Namespace) -> int:
    """Assemble and coordinate local development environment processes."""
    mgr = DevProcessManager()
    if sp := ensure_spicedb_available(host=str(args.spicedb_host), port=int(args.spicedb_port)):
        mgr.register(sp, "spicedb-pf")
    print_banner(args)

    uv = ["uv", "run"] if shutil.which("uv") else []
    ep = f"{args.spicedb_host}:{args.spicedb_port}"
    gw_env = dict(os.environ)
    gw_env["GATEWAY_PORT"] = str(args.gateway_port)
    gw_env["GATEWAY_HOST"] = str(args.gateway_host)
    gw_env["RUNEFOBLE_SPICEDB_ENDPOINT"] = gw_env["SPICEDB_ENDPOINT"] = ep
    main_py = "gateway/api/src/gateway_api/main.py"
    gw_cmd = [*uv, "python", main_py] if uv else [sys.executable, main_py]
    gw = mgr.launch(DevService("gateway", gw_cmd, REPO_ROOT, gw_env, CYAN))

    if args.worker:
        w_cmd = [*uv, "runefoble-inference-worker"] if uv else ["runefoble-inference-worker"]
        mgr.launch(DevService("worker", w_cmd, REPO_ROOT, color=MAGENTA))

    if not wait_for_gateway(args.gateway_host, args.gateway_port, gw, args.timeout):
        mgr.terminate_all()
        return 1

    if not args.no_frontend:
        u = f"{args.gateway_host}:{args.gateway_port}"
        f_env = dict(os.environ, CHOKIDAR_USEPOLLING="true")
        f_env["GATEWAY_API_URL"], f_env["GATEWAY_WS_URL"] = f"http://{u}", f"ws://{u}"
        f_cmd = ["pnpm", "run", "dev", "--host", "0.0.0.0", "--port", str(args.frontend_port)]
        mgr.launch(DevService("frontend", f_cmd, REPO_ROOT / "frontend", f_env, GREEN))
        msg = f"{GREEN}[dev-orchestrator] Ready at http://localhost:{args.frontend_port}\033[0m\n"
        print(msg, flush=True)

    return mgr.monitor()


def main() -> None:
    """CLI entrypoint."""
    sys.exit(run_orchestrator(parse_args()))


if __name__ == "__main__":
    main()
