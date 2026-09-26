"""Test helper to launch and manage the Audience Studio Fastify server."""

import os
import socket
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def get_free_port() -> int:
    """Find an available port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_audience_studio_server() -> Generator[str]:
    """Start Audience Studio Fastify server as subprocess and yield base URL."""
    port = get_free_port()
    base_url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["PORT"] = str(port)
    env["HOST"] = "127.0.0.1"
    env["NODE_ENV"] = "test"
    env["REDIS_URL"] = "mock://redis"

    dist_index = REPO_ROOT / "services" / "audience_studio" / "dist" / "index.js"
    src_index = REPO_ROOT / "services" / "audience_studio" / "src" / "index.ts"

    if dist_index.is_file():
        cmd = ["node", str(dist_index)]
    else:
        cmd = ["node", "--experimental-strip-types", str(src_index)]

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to become healthy
    deadline = time.time() + 8.0
    healthy = False
    with httpx.Client(base_url=base_url) as client:
        while time.time() < deadline:
            try:
                res = client.get("/healthz", timeout=1.0)
                if res.status_code == 200:
                    healthy = True
                    break
            except Exception:
                time.sleep(0.1)

    if not healthy:
        proc.terminate()
        stdout, stderr = proc.communicate(timeout=2.0)
        raise RuntimeError(
            f"Audience Studio server failed to start on {base_url}:\n"
            f"STDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
        )

    try:
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
