"""Command line interface of the local development orchestrator (`make dev`)."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from .orchestrator import run_orchestrator


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


def main() -> None:
    """Entry point."""
    args = parse_args()
    sys.exit(run_orchestrator(args))
