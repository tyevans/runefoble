"""ANSI color formatting constants and banner display for Runefoble dev CLI."""

from __future__ import annotations

from typing import Any

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BOLD = "\033[1m"
RESET = "\033[0m"

__all__ = ["BOLD", "CYAN", "GREEN", "MAGENTA", "RED", "RESET", "YELLOW", "print_banner"]


def print_banner(
    gw_host_or_args: Any = "127.0.0.1",
    gw_port: int = 8000,
    sp_host: str = "127.0.0.1",
    sp_port: int = 50051,
    fe_port: int | None = None,
    worker: bool = False,
) -> None:
    """Print the Runefoble local development environment banner."""
    if hasattr(gw_host_or_args, "gateway_host"):
        args = gw_host_or_args
        gw_host, gw_port = str(args.gateway_host), int(args.gateway_port)
        sp_host, sp_port = str(args.spicedb_host), int(args.spicedb_port)
        fe_port = None if getattr(args, "no_frontend", False) else int(args.frontend_port)
        worker = bool(getattr(args, "worker", False))
    else:
        gw_host = str(gw_host_or_args)

    print(f"{BOLD}{MAGENTA}======================================================{RESET}")
    print(f"{BOLD}{MAGENTA}       Runefoble Local Development Environment        {RESET}")
    print(f"{BOLD}{MAGENTA}======================================================{RESET}")
    print(f"{CYAN}  * API Gateway:{RESET}     http://{gw_host}:{gw_port}")
    print(f"{CYAN}  * SpiceDB gRPC:{RESET}    {sp_host}:{sp_port}")
    if fe_port is not None:
        print(f"{CYAN}  * Vite Frontend:{RESET}   http://localhost:{fe_port}")
    if worker:
        print(f"{CYAN}  * Inference Worker:{RESET} active")
    print(f"{BOLD}{MAGENTA}------------------------------------------------------{RESET}\n")
