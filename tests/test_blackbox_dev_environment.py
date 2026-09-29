"""Blackbox integration tests for local development environment (make dev) and Vite proxy.

Asserts:
1. Makefile targets and help documentation include 'dev'.
2. Dev server orchestrator CLI parsing, health polling, and clean process termination.
3. API Gateway CORS readiness for http://localhost:5173 and all health endpoint aliases.
4. Vite proxy configuration routing (/api, /api/v1, /ws, /docs, /openapi.json, /mail, /oauth).
5. Live end-to-end proxying through Vite dev server to backend endpoints without 502 errors.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from scripts.dev_server import (
    parse_args,
    terminate_processes,
    wait_for_health,
)


def find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MockBackendHandler(http.server.BaseHTTPRequestHandler):
    """Mock backend server to verify Vite proxy dispatch."""

    def do_GET(self) -> None:  # noqa: N802
        response_payload = {
            "path": self.path,
            "headers": dict(self.headers),
            "status": "success",
        }
        encoded = json.dumps(response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        """Suppress stdout log spam during test runs."""
        pass


def test_makefile_dev_target_and_help():
    """Verify that 'make dev' is defined in Makefile and documented in 'make help'."""
    proc = subprocess.run(["make", "help"], capture_output=True, text=True, check=True)
    assert "dev " in proc.stdout
    assert "Run API Gateway and Vite frontend concurrently" in proc.stdout

    dry_run = subprocess.run(["make", "-n", "dev"], capture_output=True, text=True, check=True)
    assert "scripts/dev_server.py" in dry_run.stdout


def test_dev_server_cli_args():
    """Verify scripts/dev_server.py CLI argument defaults and overrides."""
    args = parse_args([])
    assert args.gateway_port == 8000
    assert args.frontend_port == 5173
    assert args.host == "127.0.0.1"
    assert args.health_timeout == 30.0
    assert not args.with_worker
    assert not args.no_frontend
    assert not args.no_gateway

    custom_args = parse_args(
        [
            "--gateway-port",
            "9000",
            "--frontend-port",
            "6173",
            "--with-worker",
            "--no-frontend",
            "--health-timeout",
            "10.0",
        ]
    )
    assert custom_args.gateway_port == 9000
    assert custom_args.frontend_port == 6173
    assert custom_args.with_worker is True
    assert custom_args.no_frontend is True
    assert custom_args.health_timeout == 10.0


def test_dev_server_wait_for_health():
    """Verify wait_for_health returns True on HTTP 200 and False on unreachable server."""
    port = find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), MockBackendHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        url = f"http://127.0.0.1:{port}/healthz"
        assert wait_for_health(url, timeout=3.0, interval=0.1) is True

        dead_url = f"http://127.0.0.1:{find_free_port()}/healthz"
        assert wait_for_health(dead_url, timeout=0.5, interval=0.1) is False
    finally:
        server.shutdown()


def test_dev_server_terminate_processes():
    """Verify terminate_processes cleanly halts running subprocesses."""
    proc = subprocess.Popen(["sleep", "60"])
    assert proc.poll() is None
    terminate_processes([proc], timeout=1.0)
    assert proc.poll() is not None


def test_gateway_cors_and_health_endpoints():
    """Verify Gateway API provides required health endpoints and permits Vite dev origin CORS."""
    client = TestClient(gateway_app)

    # Health endpoint aliases
    for path in ["/healthz", "/health", "/api/v1/health"]:
        res = client.get(path)
        assert res.status_code == 200, f"Endpoint {path} failed: {res.text}"
        data = res.json()
        assert data["status"] == "healthy"

    # Preflight CORS check for Vite frontend (http://localhost:5173)
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,authorization",
    }
    cors_res = client.options("/api/v1/campaigns", headers=headers)
    assert cors_res.status_code == 200
    assert cors_res.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert cors_res.headers.get("access-control-allow-credentials") == "true"


def test_vite_config_proxy_rules():
    """Inspect frontend/vite.config.ts to verify all backend and proxy routes are defined."""
    vite_conf_path = Path("frontend/vite.config.ts")
    assert vite_conf_path.exists(), "frontend/vite.config.ts must exist"
    content = vite_conf_path.read_text()

    required_proxies = [
        "'/api/v1'",
        "'/api'",
        "'/ws'",
        "'/docs'",
        "'/openapi.json'",
        "'/mail'",
        "'/mailpit'",
        "'/oauth'",
        "'/auth'",
    ]
    for proxy in required_proxies:
        assert proxy in content, f"Proxy route {proxy} missing from frontend/vite.config.ts"

    # Verify WebSocket proxy is configured with ws: true
    assert re.search(r"'/ws':\s*\{\s*target:\s*gatewayWsUrl,\s*ws:\s*true", content)


@pytest.mark.asyncio
async def test_live_vite_proxy_forwarding():
    """Start mock backend and Vite dev server, verifying seamless proxying without 502 errors."""
    mock_backend_port = find_free_port()
    mock_mailpit_port = find_free_port()
    vite_port = find_free_port()

    # Start mock gateway and mock mailpit servers
    backend_server = http.server.HTTPServer(("127.0.0.1", mock_backend_port), MockBackendHandler)
    backend_thread = threading.Thread(target=backend_server.serve_forever, daemon=True)
    backend_thread.start()

    mailpit_server = http.server.HTTPServer(("127.0.0.1", mock_mailpit_port), MockBackendHandler)
    mailpit_thread = threading.Thread(target=mailpit_server.serve_forever, daemon=True)
    mailpit_thread.start()

    env = os.environ.copy()
    env["GATEWAY_API_URL"] = f"http://127.0.0.1:{mock_backend_port}"
    env["MAILPIT_URL"] = f"http://127.0.0.1:{mock_mailpit_port}"
    env["CHOKIDAR_USEPOLLING"] = "true"

    vite_proc = subprocess.Popen(
        [
            "pnpm",
            "run",
            "dev",
            "--port",
            str(vite_port),
            "--host",
            "127.0.0.1",
        ],
        cwd="frontend",
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for Vite dev server to be ready
        vite_ready = False
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{vite_port}/")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        vite_ready = True
                        break
            except Exception:
                time.sleep(0.3)

        assert vite_ready, "Vite dev server failed to start within timeout"

        # Verify proxy routes do not return 502 Bad Gateway
        endpoints_to_test = [
            f"http://127.0.0.1:{vite_port}/api/v1/health",
            f"http://127.0.0.1:{vite_port}/api/campaigns",
            f"http://127.0.0.1:{vite_port}/docs",
            f"http://127.0.0.1:{vite_port}/openapi.json",
            f"http://127.0.0.1:{vite_port}/mail/api/v1/messages",
        ]

        for url in endpoints_to_test:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                assert resp.status == 200, (
                    f"Proxy request to {url} returned non-200 status {resp.status}"
                )
                data = json.loads(resp.read().decode("utf-8"))
                assert data["status"] == "success"

    finally:
        terminate_processes([vite_proc], timeout=2.0)
        backend_server.shutdown()
        mailpit_server.shutdown()
