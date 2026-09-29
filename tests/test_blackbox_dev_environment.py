"""Blackbox tests for Local Development Workflow (make dev) and Vite Proxy Gateway Routing.

Governed by ADR-0004, ADR-0010, and ADR-0013.
Part of TASK-0352.
"""

from __future__ import annotations

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

REPO_ROOT = Path(__file__).resolve().parent.parent


def get_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_makefile_dev_target():
    """Verify that 'make dev' is declared in Makefile and documented in 'make help'."""
    # 1. Verify dry-run
    res_dry = subprocess.run(["make", "-n", "dev"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert res_dry.returncode == 0, f"'make -n dev' failed: {res_dry.stderr}"
    assert "scripts/dev_server.py" in res_dry.stdout

    # 2. Verify make help documentation
    res_help = subprocess.run(["make", "help"], cwd=REPO_ROOT, capture_output=True, text=True)
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
    unused_port = get_free_port()
    assert is_port_open("127.0.0.1", unused_port) is False


def test_gateway_health_probes_and_cors():
    """Verify Gateway API health endpoints and CORS configuration for localhost:5173."""
    client = TestClient(gateway_app)

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
    unused_port = get_free_port()
    assert check_health("127.0.0.1", unused_port, timeout=0.1) is False
    assert wait_for_gateway("127.0.0.1", unused_port, timeout=0.4, poll_interval=0.1) is False

    # 2. Test success against active server
    mock_port = get_free_port()

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


def test_vite_config_proxy_rules():
    """Verify frontend/vite.config.ts expands proxying for all required endpoints."""
    vite_config_path = REPO_ROOT / "frontend" / "vite.config.ts"
    assert vite_config_path.exists(), "frontend/vite.config.ts must exist"
    content = vite_config_path.read_text()

    required_proxies = [
        "'/api/v1'",
        "'/api'",
        "'/ws'",
        "'/docs'",
        "'/openapi.json'",
        "'/mail'",
        "'/oauth'",
        "'/auth'",
    ]
    for p in required_proxies:
        assert p in content, f"Missing proxy rule {p} in vite.config.ts"

    assert "ws: true" in content, "WebSocket proxy must declare ws: true"
    assert "configure: (proxy)" in content, "WebSocket proxy must provide error resilience"


def test_blackbox_live_vite_proxy_to_gateway():
    """End-to-end blackbox test: Start mock backend and Vite dev server, verifying seamless proxying."""
    gw_port = get_free_port()
    mail_port = get_free_port()
    vite_port = get_free_port()

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


def test_orchestrator_live_full_flow():
    """Verify complete make dev workflow: starts Gateway and Vite concurrently and cleanly stops."""
    import signal

    gw_port = get_free_port()
    vite_port = get_free_port()

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

    assert proc.returncode in (0, -signal.SIGINT)
