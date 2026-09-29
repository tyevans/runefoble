"""Unit and blackbox tests for modular dev_orchestrator submodules.

Governed by ADR-0003, ADR-0010, and ADR-0013. Part of TASK-0434.
"""

from __future__ import annotations

import http.server
import socket
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import scripts.dev_orchestrator as dev_orchestrator
from scripts.dev_orchestrator.colors import (
    BOLD,
    CYAN,
    GREEN,
    MAGENTA,
    RED,
    RESET,
    YELLOW,
    print_banner,
)
from scripts.dev_orchestrator.health import check_health, wait_for_gateway, wait_for_gateway_healthy
from scripts.dev_orchestrator.ports import ensure_spicedb_available, is_port_open
from scripts.dev_orchestrator.runner import (
    DevProcessManager,
    DevService,
    pipe_output,
    pipe_stream,
    terminate_processes,
)
from scripts.dev_server import (
    check_health as server_check_health,
)
from scripts.dev_server import (
    is_port_open as server_is_port_open,
)
from scripts.dev_server import (
    main as server_main,
)
from scripts.dev_server import (
    parse_args as server_parse_args,
)
from scripts.dev_server import (
    run_orchestrator as server_run_orchestrator,
)
from scripts.dev_server import (
    terminate_processes as server_terminate_processes,
)
from scripts.dev_server import (
    wait_for_gateway as server_wait_for_gateway,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_colors_constants_and_banner(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify ANSI color definitions and banner output formatting."""
    for c in [BOLD, CYAN, GREEN, MAGENTA, RED, RESET, YELLOW]:
        assert isinstance(c, str) and len(c) > 0

    args = MagicMock()
    args.gateway_host = "127.0.0.1"
    args.gateway_port = 8000
    args.spicedb_host = "127.0.0.1"
    args.spicedb_port = 50051
    args.no_frontend = False
    args.frontend_port = 5173
    args.worker = True

    print_banner(args)
    captured = capsys.readouterr().out
    assert "Runefoble Local Development Environment" in captured
    assert "http://127.0.0.1:8000" in captured
    assert "127.0.0.1:50051" in captured
    assert "http://localhost:5173" in captured
    assert "Inference Worker:" in captured


def test_ports_probing_and_spicedb_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify port probing detection and SpiceDB mock environment bypass."""
    free_port = get_free_port()
    assert is_port_open("127.0.0.1", free_port) is False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", free_port))
        s.listen(1)
        assert is_port_open("127.0.0.1", free_port) is True

    monkeypatch.setenv("SPICEDB_ENDPOINT", "mock")
    assert ensure_spicedb_available(host="127.0.0.1", port=free_port) is None


def test_health_checking_and_waiter() -> None:
    """Verify check_health and wait_for_gateway_healthy behavior."""
    free_port = get_free_port()
    assert check_health("127.0.0.1", free_port, timeout=0.1) is False
    assert (
        wait_for_gateway_healthy(
            "127.0.0.1", free_port, gateway_proc=None, timeout=0.3, poll_interval=0.1
        )
        is False
    )

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')

        def log_message(self, format: str, *args: object) -> None:
            pass

    server_port = get_free_port()
    httpd = http.server.HTTPServer(("127.0.0.1", server_port), HealthHandler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    try:
        assert check_health("127.0.0.1", server_port, timeout=1.0) is True
        assert wait_for_gateway("127.0.0.1", server_port, timeout=1.0, poll_interval=0.1) is True
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_runner_process_manager_and_service() -> None:
    """Verify DevService model and DevProcessManager lifecycle management."""
    assert pipe_output is pipe_stream

    svc = DevService(
        name="test-proc",
        cmd=["python3", "-c", "import time; time.sleep(10)"],
        cwd=REPO_ROOT,
        color=CYAN,
    )
    assert svc.name == "test-proc"
    assert svc.color == CYAN

    mgr = DevProcessManager()
    proc = mgr.launch(svc)
    assert proc.poll() is None
    assert len(mgr.processes) == 1

    mgr.terminate_all()
    assert proc.poll() is not None


def test_dev_server_facade_contract() -> None:
    """Verify that scripts.dev_server re-exports match dev_orchestrator public APIs."""
    assert dev_orchestrator.check_health is check_health
    assert server_check_health is check_health
    assert server_is_port_open is is_port_open
    assert server_terminate_processes is terminate_processes
    assert server_wait_for_gateway is wait_for_gateway
    assert callable(server_parse_args)
    assert callable(server_run_orchestrator)
    assert callable(server_main)

    args = server_parse_args(["--gateway-port", "8123"])
    assert args.gateway_port == 8123
    assert args.frontend_port == 5173
    assert args.worker is False
