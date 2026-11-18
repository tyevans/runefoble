"""Blackbox tests for Local Development Workflow (make dev) and Vite Proxy Gateway Routing.

Governed by ADR-0004, ADR-0010, and ADR-0013.
Part of TASK-0352.
"""

from __future__ import annotations

import contextlib
import http.server
import os
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from scripts.dev_server import (
    check_health,
    is_port_open,
    parse_args,
    terminate_processes,
    wait_for_gateway,
)
from tests.helpers.ports import free_port
from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_makefile_dev_target():
    """Verify that 'make dev' is declared in Makefile and documented in 'make help'."""
    # 1. Verify dry-run
    res_dry = run_command(["make", "-n", "dev"], cwd=REPO_ROOT, timeout=240.0)
    assert res_dry.returncode == 0, f"'make -n dev' failed: {res_dry.stderr}"
    assert "scripts/dev_server.py" in res_dry.stdout

    # 2. Verify make help documentation
    res_help = run_command(["make", "help"], cwd=REPO_ROOT, timeout=240.0)
    assert res_help.returncode == 0
    assert "dev " in res_help.stdout
    assert "Run API Gateway and Vite frontend concurrently" in res_help.stdout


def test_orchestrator_cli_parsing():
    """Verify scripts/dev_server.py argument parsing and default configuration."""
    args = parse_args(
        [
            "--gateway-port",
            "8090",
            "--frontend-port",
            "5190",
            "--worker",
            "--no-frontend",
            "--timeout",
            "12.5",
        ]
    )
    assert args.gateway_port == 8090
    assert args.frontend_port == 5190
    assert args.worker is True
    assert args.no_frontend is True
    assert args.timeout == 12.5
    assert args.spicedb_port == 50051
    assert args.spicedb_host == "127.0.0.1"

    # Custom spicedb arguments
    custom_args = parse_args(["--spicedb-port", "50099", "--spicedb-host", "10.0.0.1"])
    assert custom_args.spicedb_port == 50099
    assert custom_args.spicedb_host == "10.0.0.1"

    # is_port_open returns False on unused port
    unused_port = free_port()
    assert is_port_open("127.0.0.1", unused_port) is False


def test_gateway_health_probes_and_cors():
    """Verify Gateway API health endpoints and CORS configuration for localhost:5173."""
    with TestClient(gateway_app) as client:
        _check_health_and_cors(client)


def _check_health_and_cors(client: TestClient) -> None:

    # Health endpoints
    for route in ["/healthz", "/health", "/api/v1/health"]:
        resp = client.get(route)
        assert resp.status_code == 200, f"Expected 200 for {route}, got {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "healthy"
        assert data.get("gateway") == "runefoble-api-gateway"

    # CORS verification for Vite dev origin
    cors_resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert cors_resp.status_code == 200
    assert cors_resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert cors_resp.headers.get("access-control-allow-credentials") == "true"


def test_orchestrator_health_waiter_live_and_timeout():
    """Verify dev orchestrator health check polling and timeout behavior."""
    # 1. Test timeout on unreachable port
    unused_port = free_port()
    assert check_health("127.0.0.1", unused_port, timeout=0.1) is False
    assert wait_for_gateway("127.0.0.1", unused_port, timeout=0.4, poll_interval=0.1) is False

    # 2. Test success against active server
    mock_port = free_port()

    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')

        def log_message(self, format, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", mock_port), HealthHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        assert check_health("127.0.0.1", mock_port, timeout=1.0) is True
        assert wait_for_gateway("127.0.0.1", mock_port, timeout=2.0, poll_interval=0.1) is True
    finally:
        server.shutdown()
        server.server_close()


def test_blackbox_live_vite_proxy_to_gateway():
    """End-to-end blackbox test: Start mock backend and Vite dev server, verifying seamless proxying."""
    gw_port = free_port()
    mail_port = free_port()
    vite_port = free_port()

    class GatewayMockHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"service": "gateway", "path": "{self.path}"}}'.encode())

        def log_message(self, format, *args):
            pass

    class MailpitMockHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"service": "mailpit", "messages": []}')

        def log_message(self, format, *args):
            pass

    gw_server = http.server.HTTPServer(("127.0.0.1", gw_port), GatewayMockHandler)
    mail_server = http.server.HTTPServer(("127.0.0.1", mail_port), MailpitMockHandler)

    threading.Thread(target=gw_server.serve_forever, daemon=True).start()
    threading.Thread(target=mail_server.serve_forever, daemon=True).start()

    env = os.environ.copy()
    env["GATEWAY_API_URL"] = f"http://127.0.0.1:{gw_port}"
    env["MAILPIT_URL"] = f"http://127.0.0.1:{mail_port}"
    env["CHOKIDAR_USEPOLLING"] = "true"

    vite_proc = subprocess.Popen(
        ["pnpm", "exec", "vite", "--host", "0.0.0.0", "--port", str(vite_port)],
        cwd=REPO_ROOT / "frontend",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        # Wait for Vite dev server to boot
        vite_ready = False
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{vite_port}/api/v1/health", timeout=1.0
                ) as resp:
                    if resp.status == 200:
                        vite_ready = True
                        break
            except Exception:
                time.sleep(0.3)

        if not vite_ready and vite_proc.stdout:
            logs = vite_proc.stdout.read().decode(errors="replace")
            print(f"Vite dev server logs on startup failure:\n{logs}")

        assert vite_ready, "Vite dev server failed to start within timeout"

        # Assert proxy endpoints through Vite
        test_routes = [
            ("/api/v1/health", "gateway"),
            ("/api/v1/campaigns", "gateway"),
            ("/api/users", "gateway"),
            ("/docs", "gateway"),
            ("/openapi.json", "gateway"),
            ("/mail/messages", "mailpit"),
        ]

        for path, expected_service in test_routes:
            url = f"http://127.0.0.1:{vite_port}{path}"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                assert resp.status == 200, f"Expected 200 from {url}, got {resp.status}"
                body = resp.read().decode()
                assert expected_service in body, f"Expected '{expected_service}' in body for {path}"

    finally:
        terminate_processes([vite_proc])
        gw_server.shutdown()
        gw_server.server_close()
        mail_server.shutdown()
        mail_server.server_close()


def test_orchestrator_process_termination_group():
    """Verify terminate_processes cleanly halts processes and child process groups."""
    proc = subprocess.Popen(
        ["python3", "-c", "import time; time.sleep(30)"],
        start_new_session=True,
    )
    assert proc.poll() is None
    terminate_processes([proc])
    assert proc.poll() is not None


def test_orchestrator_exits_when_redis_is_unreachable():
    """The orchestrator refuses to start when no Redis answers. It does not start a gateway.

    KUBECONFIG names a missing file, so no Kind cluster can supply Redis through a port-forward.
    """
    env = {
        **os.environ,
        "RUNEFOBLE_REDIS_URL": f"redis://127.0.0.1:{free_port()}/0",
        "KUBECONFIG": str(REPO_ROOT / ".no-such-kubeconfig"),
    }
    result = run_command(
        ["python3", "scripts/dev_server.py", "--gateway-port", str(free_port()), "--no-frontend"],
        cwd=REPO_ROOT,
        env=env,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Redis is not reachable" in result.stdout


class _RespServer(threading.Thread):
    """Minimal Redis protocol server on a loopback port. It answers PING and accepts any command.

    Redis is an external process. The gateway only needs it to answer the start-up ping.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(8)
        self.port = self._server.getsockname()[1]

    def run(self) -> None:
        while True:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    @staticmethod
    def _serve(conn: socket.socket) -> None:
        """Read RESP array commands from a buffer and send one reply per command."""
        buffer = b""
        with conn:
            while chunk := conn.recv(4096):
                buffer += chunk
                while (parsed := _RespServer._take_command(buffer)) is not None:
                    command, buffer = parsed
                    name = command[0].upper() if command else b""
                    conn.sendall(b"+PONG\r\n" if name == b"PING" else b"+OK\r\n")

    @staticmethod
    def _take_command(buffer: bytes) -> tuple[list[bytes], bytes] | None:
        """Return one complete command and the remaining bytes, or None when incomplete."""
        if not buffer.startswith(b"*"):
            return None
        head, sep, rest = buffer.partition(b"\r\n")
        if not sep:
            return None
        parts: list[bytes] = []
        for _ in range(int(head[1:])):
            size_line, sep, rest = rest.partition(b"\r\n")
            if not sep:
                return None
            size = int(size_line[1:])
            if len(rest) < size + 2:
                return None
            parts.append(rest[:size])
            rest = rest[size + 2 :]
        return parts, rest

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._server.shutdown(socket.SHUT_RDWR)  # wakes the thread blocked in accept()
        self._server.close()


def test_orchestrator_live_full_flow():
    """Verify complete make dev workflow: starts Gateway and Vite concurrently and cleanly stops."""
    import signal

    redis_server = _RespServer()
    redis_server.start()

    gw_port = free_port()
    vite_port = free_port()

    proc = subprocess.Popen(
        [
            "python3",
            "scripts/dev_server.py",
            "--gateway-port",
            str(gw_port),
            "--frontend-port",
            str(vite_port),
            "--timeout",
            "30",
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "RUNEFOBLE_REDIS_URL": f"redis://127.0.0.1:{redis_server.port}/0"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        # Wait for Vite dev server and proxy to become ready
        ready = False
        deadline = time.monotonic() + 35.0
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{vite_port}/api/v1/health", timeout=1.0
                ) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.3)

        if not ready and proc.stdout:
            logs = proc.stdout.read().decode(errors="replace")
            print(f"Dev orchestrator logs on startup failure:\n{logs}")

        assert ready, "Full dev orchestrator failed to bring up Vite proxy"

        # Verify gateway direct health
        with urllib.request.urlopen(f"http://127.0.0.1:{gw_port}/healthz", timeout=2.0) as resp:
            assert resp.status == 200

    finally:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            proc.wait(timeout=6.0)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=2.0)
        redis_server.close()

    assert proc.returncode in (0, -signal.SIGINT)
